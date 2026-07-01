from app.db.models import RawItem, Source
from app.services.ingestion import normalize_item
from app.sources.hugging_face import (
    HuggingFaceConnector,
    as_payload_list,
    hugging_face_traction_signal,
)


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
    assert item.raw_metadata["hf_kind"] == "model"
    assert item.raw_metadata["downloads"] == 120000
    assert item.raw_metadata["traction_signal"] == (
        "Hugging Face model traction: 120K downloads, 4.2K likes"
    )
    assert "Hugging Face model traction" in item.raw_text
    assert item.published_at is not None


def test_hugging_face_connector_converts_dataset_to_raw_item() -> None:
    connector = HuggingFaceConnector(limit=3)

    item = connector._dataset_to_raw_item(
        {
            "id": "openai/gsm8k",
            "tags": ["benchmark", "reasoning", "llm"],
            "downloads": 90000,
            "likes": 1200,
            "lastModified": "2026-06-25T10:30:00.000Z",
        }
    )

    assert item is not None
    assert item.external_id == "dataset:openai/gsm8k"
    assert item.url == "https://huggingface.co/datasets/openai/gsm8k"
    assert item.raw_author == "openai"
    assert item.raw_metadata["hf_kind"] == "dataset"
    assert item.raw_metadata["traction_signal"] == (
        "Hugging Face dataset traction: 90K downloads, 1.2K likes"
    )
    assert "Dataset: openai/gsm8k" in item.raw_text


def test_hugging_face_connector_converts_space_to_raw_item() -> None:
    connector = HuggingFaceConnector(limit=3)

    item = connector._space_to_raw_item(
        {
            "id": "demo-org/video-agent",
            "sdk": "gradio",
            "tags": ["video", "agent", "productivity"],
            "likes": 640,
            "lastModified": "2026-06-25T10:30:00.000Z",
        }
    )

    assert item is not None
    assert item.external_id == "space:demo-org/video-agent"
    assert item.url == "https://huggingface.co/spaces/demo-org/video-agent"
    assert item.raw_author == "demo-org"
    assert item.raw_metadata["hf_kind"] == "space"
    assert item.raw_metadata["traction_signal"] == "Hugging Face Space traction: 640 likes"
    assert "Space demo: demo-org/video-agent" in item.raw_text


def test_hugging_face_connector_skips_model_without_id() -> None:
    connector = HuggingFaceConnector()

    assert connector._model_to_raw_item({"tags": ["llm"]}) is None


def test_hugging_face_space_normalizes_as_product_demo() -> None:
    source = Source(id=1, name="Hugging Face", type="model_hub", access_method="api")
    raw = RawItem(
        id=1,
        source_id=1,
        external_id="space:demo-org/video-agent",
        url="https://huggingface.co/spaces/demo-org/video-agent",
        raw_title="demo-org/video-agent: Hugging Face Space update",
        raw_text="AI video agent product demo with multimodal workflow automation.",
        raw_metadata={
            "hf_kind": "space",
            "traction_signal": "Hugging Face Space traction: 640 likes",
        },
        content_hash="abc",
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "product"
    assert item.subcategory == "product_media"
    assert item.source_quality_score == 0.78
    assert item.summary_short == "Hugging Face Space: demo-org/video-agent: Hugging Face Space update"
    assert "Traction signal: Hugging Face Space traction: 640 likes" in item.summary_detailed


def test_hugging_face_dataset_normalizes_as_research_release() -> None:
    source = Source(id=1, name="Hugging Face", type="model_hub", access_method="api")
    raw = RawItem(
        id=1,
        source_id=1,
        external_id="dataset:openai/gsm8k",
        url="https://huggingface.co/datasets/openai/gsm8k",
        raw_title="openai/gsm8k: Hugging Face dataset update",
        raw_text="AI reasoning benchmark dataset for LLM evaluation.",
        raw_metadata={
            "hf_kind": "dataset",
            "traction_signal": "Hugging Face dataset traction: 90K downloads, 1.2K likes",
        },
        content_hash="abc",
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "research"
    assert item.subcategory == "dataset_release"
    assert item.source_quality_score == 0.78
    assert item.summary_short == "Hugging Face dataset: openai/gsm8k: Hugging Face dataset update"
    assert "Engagement signal: Hugging Face dataset traction" in item.summary_detailed


def test_hugging_face_traction_signal_formats_counts() -> None:
    assert hugging_face_traction_signal("model", downloads=1_250_000, likes=4200) == (
        "Hugging Face model traction: 1.2M downloads, 4.2K likes"
    )
    assert hugging_face_traction_signal("space", likes=12) == (
        "Hugging Face Space traction: 12 likes"
    )
    assert hugging_face_traction_signal("dataset") is None


def test_as_payload_list_accepts_list_and_wrapped_items() -> None:
    assert as_payload_list([{"id": "a"}, "bad"]) == [{"id": "a"}]
    assert as_payload_list({"items": [{"id": "b"}]}) == [{"id": "b"}]
    assert as_payload_list({"results": [{"id": "c"}]}) == [{"id": "c"}]
    assert as_payload_list({"unexpected": []}) == []
