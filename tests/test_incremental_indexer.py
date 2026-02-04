def test_rag_system_has_add_documents():
    from persistent_storage import rag_system

    assert hasattr(rag_system, "add_documents")
