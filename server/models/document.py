class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    filepath = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    # file_hash column completely removed
    # Other columns...
