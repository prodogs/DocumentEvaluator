"""
LLM Responses API Routes

Provides endpoints for querying and viewing LLM responses from the KnowledgeDocuments database.
"""

import logging
from flask import Blueprint, jsonify, request
import psycopg2
from datetime import datetime
import json

logger = logging.getLogger(__name__)

llm_responses_bp = Blueprint('llm_responses', __name__)

def get_kb_connection():
    """Get connection to KnowledgeDocuments database"""
    return psycopg2.connect(
        host="studio.local",
        database="KnowledgeDocuments",
        user="postgres",
        password="prodogs03",
        port=5432
    )

@llm_responses_bp.route('/api/llm-responses', methods=['GET'])
def get_llm_responses():
    """
    Get paginated list of LLM responses with filtering and sorting
    
    Query Parameters:
    - limit: Number of items per page (default: 50)
    - offset: Number of items to skip (default: 0)
    - search: Search term for document names, prompts, or response text
    - status: Filter by status (COMPLETED, FAILED, PROCESSING, QUEUED)
    - batch_id: Filter by batch ID
    - min_score: Minimum overall score filter
    - max_score: Maximum overall score filter
    - start_date: Start date filter (ISO format)
    - end_date: End date filter (ISO format)
    - sort: Sort order (created_desc, created_asc, score_desc, score_asc, duration_desc, duration_asc)
    """
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        batch_id = request.args.get('batch_id', '')
        min_score = request.args.get('min_score', '')
        max_score = request.args.get('max_score', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        sort = request.args.get('sort', 'created_desc')
        
        # Build query - cannot do cross-database joins, so just get llm_responses
        query = """
            SELECT 
                lr.id,
                lr.document_id,
                lr.prompt_id,
                lr.connection_id,
                lr.batch_id,
                lr.status,
                lr.response_text,
                lr.overall_score,
                lr.error_message,
                lr.input_tokens,
                lr.output_tokens,
                lr.response_time_ms,
                lr.created_at,
                lr.started_processing_at,
                lr.completed_processing_at,
                lr.task_id,
                lr.connection_details,
                lr.response_json
            FROM llm_responses lr
            WHERE 1=1
        """
        
        params = []
        
        # Add filters
        if search:
            query += """ AND (
                LOWER(kd.filename) LIKE LOWER(%s) OR
                LOWER(kd.filepath) LIKE LOWER(%s) OR
                LOWER(lr.response_text) LIKE LOWER(%s)
            )"""
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])
        
        if status and status != 'all':
            query += " AND lr.status = %s"
            params.append(status)
        
        if batch_id and batch_id != 'all':
            query += " AND lr.batch_id = %s"
            params.append(int(batch_id))
        
        if min_score:
            query += " AND lr.overall_score >= %s"
            params.append(float(min_score))
        
        if max_score:
            query += " AND lr.overall_score <= %s"
            params.append(float(max_score))
        
        if start_date:
            query += " AND lr.created_at >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND lr.created_at <= %s"
            params.append(f"{end_date} 23:59:59")
        
        # Add sorting
        sort_map = {
            'created_desc': 'lr.created_at DESC',
            'created_asc': 'lr.created_at ASC',
            'score_desc': 'lr.overall_score DESC NULLS LAST',
            'score_asc': 'lr.overall_score ASC NULLS LAST',
            'duration_desc': 'lr.response_time_ms DESC NULLS LAST',
            'duration_asc': 'lr.response_time_ms ASC NULLS LAST'
        }
        
        order_by = sort_map.get(sort, 'lr.created_at DESC')
        query += f" ORDER BY {order_by}"
        
        # Get total count
        # Remove the complex SELECT clause and ORDER BY to create count query
        count_base = query.split("ORDER BY")[0]
        # Replace the SELECT clause with COUNT(*)
        count_query = count_base.replace(
            """SELECT 
                lr.id,
                lr.document_id,
                lr.prompt_id,
                lr.connection_id,
                lr.batch_id,
                lr.status,
                lr.response_text,
                lr.overall_score,
                lr.error_message,
                lr.input_tokens,
                lr.output_tokens,
                lr.response_time_ms,
                lr.created_at,
                lr.started_processing_at,
                lr.completed_processing_at,
                lr.task_id,
                lr.connection_details,
                lr.response_json""",
            "SELECT COUNT(*) as total"
        )
        
        # Add pagination
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Execute queries
        conn = get_kb_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(count_query, params[:-2])  # Exclude limit/offset
        total = cursor.fetchone()[0]
        
        # Get results
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get prompts from doc_eval database
        from database import Session
        from models import Prompt
        session = Session()
        prompts = {p.id: {'description': p.description, 'prompt_text': p.prompt_text} 
                  for p in session.query(Prompt).all()}
        session.close()
        
        # Get document info from doc_eval database if needed
        document_ids = [row[1] for row in rows if row[1]]  # document_id is at index 1
        documents_info = {}
        if document_ids:
            from models import Document
            doc_session = Session()
            documents = doc_session.query(Document).filter(Document.id.in_(document_ids)).all()
            documents_info = {}
            for doc in documents:
                # Extract file info from meta_data
                meta_data = doc.meta_data or {}
                file_extension = meta_data.get('file_extension', '')
                if file_extension and file_extension.startswith('.'):
                    file_extension = file_extension[1:]  # Remove leading dot
                
                documents_info[doc.id] = {
                    'id': doc.id,
                    'filename': doc.filename, 
                    'filepath': doc.filepath,
                    'doc_type': file_extension.upper() if file_extension else 'Unknown',
                    'file_size': meta_data.get('file_size')
                }
            doc_session.close()
        
        # Format results
        responses = []
        for row in rows:
            # Row indices:
            # 0: id, 1: document_id, 2: prompt_id, 3: connection_id, 4: batch_id,
            # 5: status, 6: response_text, 7: overall_score, 8: error_message,
            # 9: input_tokens, 10: output_tokens, 11: response_time_ms, 12: created_at,
            # 13: started_processing_at, 14: completed_processing_at, 15: task_id,
            # 16: connection_details, 17: response_json
            
            # Parse connection details if stored as JSON
            connection_info = {}
            if row[16]:  # connection_details
                try:
                    connection_info = json.loads(row[16]) if isinstance(row[16], str) else row[16]
                except:
                    pass
            
            # Get document info
            doc_info = documents_info.get(row[1], {
                'id': None,
                'filename': 'Unknown', 
                'filepath': 'Unknown',
                'doc_type': 'Unknown',
                'file_size': None
            })
            
            response = {
                'id': row[0],
                'document_id': row[1],
                'kb_document_id': row[1],  # Use document_id as kb_document_id for compatibility
                'prompt_id': row[2],
                'connection_id': row[3],
                'batch_id': row[4],
                'status': row[5],
                'response_text': row[6],
                'overall_score': row[7],
                'error_message': row[8],
                'input_tokens': row[9],
                'output_tokens': row[10],
                'response_time_ms': row[11],
                'created_at': row[12].isoformat() if row[12] else None,
                'started_processing_at': row[13].isoformat() if row[13] else None,
                'completed_processing_at': row[14].isoformat() if row[14] else None,
                'task_id': row[15],
                'document': doc_info,
                'prompt': prompts.get(row[2], {  # prompt_id is at index 2
                    'description': 'Unknown prompt',
                    'prompt_text': None
                }),
                'connection': {
                    'name': connection_info.get('connection_name', 'Unknown'),
                    'model_name': connection_info.get('model_name', 'Unknown'),
                    'provider_type': connection_info.get('provider_type', 'Unknown')
                }
            }
            
            # Use response_json from database if available, otherwise try to parse response_text
            if row[17]:  # response_json
                try:
                    response['response_json'] = json.loads(row[17]) if isinstance(row[17], str) else row[17]
                except:
                    response['response_json'] = None
            elif response['response_text']:
                try:
                    response['response_json'] = json.loads(response['response_text'])
                except:
                    response['response_json'] = None
            else:
                response['response_json'] = None
            
            responses.append(response)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'responses': responses,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching LLM responses: {e}")
        return jsonify({'error': str(e)}), 500

@llm_responses_bp.route('/api/llm-responses/<int:response_id>', methods=['GET'])
def get_llm_response_detail(response_id):
    """Get detailed information for a specific LLM response"""
    try:
        conn = get_kb_connection()
        cursor = conn.cursor()
        
        # Get response details
        cursor.execute("""
            SELECT 
                lr.*,
                kd.filename,
                kd.filepath,
                kd.file_size,
                kd.mime_type,
                b.batch_name
            FROM llm_responses lr
            LEFT JOIN kb_documents kd ON lr.kb_document_id = kd.id
            LEFT JOIN doc_eval.batches b ON lr.batch_id = b.id
            WHERE lr.id = %s
        """, (response_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Response not found'}), 404
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        response_data = dict(zip(columns, row))
        
        # Format dates
        for date_field in ['created_at', 'started_processing_at', 'completed_processing_at']:
            if response_data.get(date_field):
                response_data[date_field] = response_data[date_field].isoformat()
        
        # Parse connection details
        if response_data.get('connection_details'):
            try:
                response_data['connection_details'] = json.loads(response_data['connection_details']) \
                    if isinstance(response_data['connection_details'], str) else response_data['connection_details']
            except:
                pass
        
        # Parse response text as JSON if possible
        if response_data.get('response_text'):
            try:
                response_data['response_json'] = json.loads(response_data['response_text'])
            except:
                response_data['response_json'] = None
        
        cursor.close()
        conn.close()
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching LLM response detail: {e}")
        return jsonify({'error': str(e)}), 500

@llm_responses_bp.route('/api/llm-responses/stats', methods=['GET'])
def get_llm_response_stats():
    """Get statistics about LLM responses"""
    try:
        conn = get_kb_connection()
        cursor = conn.cursor()
        
        # Get overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_responses,
                COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed,
                COUNT(CASE WHEN status = 'PROCESSING' THEN 1 END) as processing,
                COUNT(CASE WHEN status = 'QUEUED' THEN 1 END) as queued,
                AVG(overall_score) as avg_score,
                AVG(response_time_ms) as avg_response_time,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                COUNT(DISTINCT batch_id) as total_batches,
                COUNT(DISTINCT connection_id) as total_connections
            FROM llm_responses
        """)
        
        stats = cursor.fetchone()
        
        result = {
            'total_responses': stats[0] or 0,
            'completed': stats[1] or 0,
            'failed': stats[2] or 0,
            'processing': stats[3] or 0,
            'queued': stats[4] or 0,
            'avg_score': float(stats[5]) if stats[5] else 0,
            'avg_response_time': float(stats[6]) if stats[6] else 0,
            'total_input_tokens': stats[7] or 0,
            'total_output_tokens': stats[8] or 0,
            'total_batches': stats[9] or 0,
            'total_connections': stats[10] or 0
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching LLM response stats: {e}")
        return jsonify({'error': str(e)}), 500