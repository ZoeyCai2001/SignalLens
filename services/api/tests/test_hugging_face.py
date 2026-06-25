from app.sources.hugging_face import HuggingFaceConnector


def test_hugging_face_connector_converts_model_to_raw_item() -> None:
    connector = HuggingFaceConnector(limit=3)

    item = connector._model_to_raw_item(
        {
            "modelId": "meta-llama/Llama-3.1-8B-Instruct",
            "pipeline_tag": "text-generation",
            "tags": ["transformers", "llm", "inference"],
            "downloads": 120000,
            "likes": 4200,
            "lastModified": "2026-06-25T10:30:00.000Z",
            "library_name": "transformers",
        }
    )

    assert item is not None
    assert item.external_id == "meta-llama/Llama-3.1-8B-Instruct"
    assert item.url == "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct"
    assert item.raw_author == "meta-llama"
    assert "text-generation" in item.raw_text
    assert item.raw_metadata["downloads"] == 120000
    assert item.published_at is not None


def test_hugging_face_connector_skips_model_without_id() -> None:
    connector = HuggingFaceConnector()

    assert connector._model_to_raw_item({"tags": ["llm"]}) is None
