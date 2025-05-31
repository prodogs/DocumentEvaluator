import os
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect
from database import Session
from models import Folder

folder_routes = Blueprint('folder_routes', __name__)

@folder_routes.route('/api/folders', methods=['POST'])
def add_folder():
    """Add a new folder to the database."""
    try:
        data = request.get_json()
        folder_path = data.get('folder_path')
        folder_name = data.get('folder_name', os.path.basename(folder_path))

        if not folder_path:
            return jsonify({'error': 'Folder path is required'}), 400

        # Validate folder path exists on disk
        if not os.path.exists(folder_path):
            return jsonify({'error': f'Folder path does not exist: {folder_path}'}), 400

        if not os.path.isdir(folder_path):
            return jsonify({'error': f'Path is not a directory: {folder_path}'}), 400

        # Add folder to database
        session = Session()
        folder = Folder(
            folder_path=folder_path,
            folder_name=folder_name,
            active=1 if data.get('active', False) else 0  # Default to False - must preprocess first
        )
        session.add(folder)
        session.commit()

        # Return the new folder with its ID
        result = {
            'id': folder.id,
            'folder_path': folder.folder_path,
            'folder_name': folder.folder_name,
            'active': bool(folder.active),
            'created_at': folder.created_at.isoformat() if folder.created_at else None
        }
        session.close()

        return jsonify({'folder': result, 'message': 'Folder added successfully'}), 201
    except IntegrityError:
        session.rollback()
        return jsonify({'error': 'Folder path already exists in database'}), 400
    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        return jsonify({'error': str(e)}), 500

@folder_routes.route('/api/folders/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Delete a folder from the database."""
    try:
        session = Session()
        folder = session.query(Folder).filter_by(id=folder_id).first()

        if not folder:
            session.close()
            return jsonify({'error': 'Folder not found'}), 404

        session.delete(folder)
        session.commit()
        session.close()

        return jsonify({'message': f'Folder {folder_id} deleted successfully'}), 200
    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        return jsonify({'error': str(e)}), 500

@folder_routes.route('/api/folders/<int:folder_id>', methods=['PUT'])
def update_folder(folder_id):
    """Update folder information."""
    try:
        data = request.get_json()
        folder_path = data.get('folder_path')
        folder_name = data.get('folder_name')

        session = Session()
        folder = session.query(Folder).filter_by(id=folder_id).first()

        if not folder:
            session.close()
            return jsonify({'error': 'Folder not found'}), 404

        # Update fields if provided
        if folder_path:
            # Validate folder path exists on disk
            if not os.path.exists(folder_path):
                session.close()
                return jsonify({'error': f'Folder path does not exist: {folder_path}'}), 400

            if not os.path.isdir(folder_path):
                session.close()
                return jsonify({'error': f'Path is not a directory: {folder_path}'}), 400

            folder.folder_path = folder_path

        if folder_name:
            folder.folder_name = folder_name

        if 'active' in data:
            folder.active = 1 if data['active'] else 0

        session.commit()

        # Return the updated folder
        result = {
            'id': folder.id,
            'folder_path': folder.folder_path,
            'folder_name': folder.folder_name,
            'active': bool(folder.active),
            'created_at': folder.created_at.isoformat() if folder.created_at else None
        }
        session.close()

        return jsonify({'folder': result, 'message': 'Folder updated successfully'}), 200
    except IntegrityError:
        session.rollback()
        session.close()
        return jsonify({'error': 'Folder path already exists in database'}), 400
    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        return jsonify({'error': str(e)}), 500

@folder_routes.route('/api/folders/<int:folder_id>/activate', methods=['POST'])
def activate_folder(folder_id):
    """Activate a folder"""
    try:
        session = Session()
        folder = session.query(Folder).filter(Folder.id == folder_id).first()

        if not folder:
            session.close()
            return jsonify({'error': f'Folder not found: {folder_id}'}), 404

        # Check if folder has been preprocessed
        folder_status = getattr(folder, 'status', 'NOT_PROCESSED')
        if folder_status != 'READY':
            session.close()
            return jsonify({
                'error': f'Folder must be preprocessed before activation. Current status: {folder_status}. Please preprocess the folder first.'
            }), 400

        folder.active = 1
        session.commit()

        # Extract values before closing session
        folder_name = folder.folder_name
        session.close()

        return jsonify({
            'message': f'Folder {folder_id} activated successfully',
            'folder_id': folder_id,
            'folder_name': folder_name,
            'active': True
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        return jsonify({'error': str(e)}), 500

@folder_routes.route('/api/folders/<int:folder_id>/deactivate', methods=['POST'])
def deactivate_folder(folder_id):
    """Deactivate a folder"""
    try:
        session = Session()
        folder = session.query(Folder).filter(Folder.id == folder_id).first()

        if not folder:
            session.close()
            return jsonify({'error': f'Folder not found: {folder_id}'}), 404

        folder.active = 0
        session.commit()

        # Extract values before closing session
        folder_name = folder.folder_name
        session.close()

        return jsonify({
            'message': f'Folder {folder_id} deactivated successfully',
            'folder_id': folder_id,
            'folder_name': folder_name,
            'active': False
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        return jsonify({'error': str(e)}), 500