"""Tests for DataForSEO Labs / Backlinks / AI Optimization / On-Page modules.

These mock the shared `client.post` so no live API calls are made — they verify
request shaping and response parsing.
"""

from unittest.mock import patch

import pytest

from aitools.seo import ai_optim, backlinks, client, labs, onpage


# ---------------------------------------------------------------------------
# client
# ---------------------------------------------------------------------------

class TestClient:
    def test_resolve_location_known(self):
        assert client.resolve_location("tr") == 2792
        assert client.resolve_location("US") == 2840

    def test_resolve_location_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown country code"):
            client.resolve_location("zz")

    def test_resolve_language_fallback(self):
        assert client.resolve_language("en") == "en"
        assert client.resolve_language("xx") == "xx"  # pass-through

    def test_post_raises_on_bad_envelope_status(self):
        fake = _FakeResponse(200, {"status_code": 40200, "status_message": "Payment Required"})
        with patch("aitools.seo.client.httpx.post", return_value=fake), \
             patch("aitools.seo.client.require_credentials", return_value=("u", "p")):
            with pytest.raises(ValueError, match=r"\[40200\]"):
                client.post("some/path", [{}])

    def test_post_raises_on_bad_task_status(self):
        payload = {
            "status_code": 20000,
            "tasks": [{"status_code": 40501, "status_message": "Invalid Field"}],
        }
        fake = _FakeResponse(200, payload)
        with patch("aitools.seo.client.httpx.post", return_value=fake), \
             patch("aitools.seo.client.require_credentials", return_value=("u", "p")):
            with pytest.raises(ValueError, match=r"\[40501\]"):
                client.post("some/path", [{}])

    def test_post_raises_on_http_error(self):
        fake = _FakeResponse(402, {}, text="Payment required")
        with patch("aitools.seo.client.httpx.post", return_value=fake), \
             patch("aitools.seo.client.require_credentials", return_value=("u", "p")):
            with pytest.raises(ValueError, match="HTTP 402"):
                client.post("some/path", [{}])


class _FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def _task(result):
    """Build a fake first-task dict as returned by client.post."""
    return {"status_code": 20000, "cost": 0.0123, "result": result}


# ---------------------------------------------------------------------------
# labs
# ---------------------------------------------------------------------------

class TestLabs:
    def test_ranked_keywords_parses_and_shapes_request(self):
        result = [{
            "total_count": 123,
            "items": [{
                "keyword_data": {
                    "keyword": "todo app",
                    "keyword_info": {"search_volume": 1000, "cpc": 1.5, "competition_level": "LOW"},
                    "keyword_properties": {"keyword_difficulty": 22},
                },
                "ranked_serp_element": {
                    "serp_item": {"rank_group": 3, "rank_absolute": 4, "url": "https://x.com/a"}
                },
            }],
        }]
        with patch("aitools.seo.labs.client.post", return_value=_task(result)) as mock_post:
            out = labs.ranked_keywords("x.com", country="tr", language="tr", limit=10)

        path, payload = mock_post.call_args[0]
        assert path == "dataforseo_labs/google/ranked_keywords/live"
        assert payload[0]["location_code"] == 2792
        assert payload[0]["language_code"] == "tr"
        assert payload[0]["limit"] == 10
        kw = out["keywords"][0]
        assert kw["keyword"] == "todo app"
        assert kw["search_volume"] == 1000
        assert kw["keyword_difficulty"] == 22
        assert kw["rank_group"] == 3
        assert kw["url"] == "https://x.com/a"
        assert out["total_count"] == 123

    def test_keyword_difficulty_parses(self):
        result = [{"items": [
            {"keyword": "a", "keyword_difficulty": 9},
            {"keyword": "b", "keyword_difficulty": 64},
        ]}]
        with patch("aitools.seo.labs.client.post", return_value=_task(result)):
            out = labs.keyword_difficulty(["a", "b"])
        assert out["keywords"] == [
            {"keyword": "a", "keyword_difficulty": 9},
            {"keyword": "b", "keyword_difficulty": 64},
        ]

    def test_keyword_difficulty_rejects_empty(self):
        with pytest.raises(ValueError, match="No keywords"):
            labs.keyword_difficulty([])

    def test_keyword_ideas_parses_volume(self):
        result = [{"total_count": 5, "items": [
            {"keyword": "weekly planner", "keyword_info": {"search_volume": 22200, "cpc": 0.98, "competition_level": "HIGH"}},
        ]}]
        with patch("aitools.seo.labs.client.post", return_value=_task(result)):
            out = labs.keyword_ideas(["daily planner"])
        assert out["keywords"][0]["search_volume"] == 22200
        assert out["keywords"][0]["competition_level"] == "HIGH"

    def test_keyword_suggestions_shapes_seed(self):
        result = [{"items": []}]
        with patch("aitools.seo.labs.client.post", return_value=_task(result)) as mock_post:
            labs.keyword_suggestions("daily planner", limit=7)
        _, payload = mock_post.call_args[0]
        assert payload[0]["keyword"] == "daily planner"
        assert payload[0]["limit"] == 7

    def test_search_intent_parses(self):
        result = [{"items": [{
            "keyword": "daily planner",
            "keyword_intent": {"label": "informational", "probability": 0.38},
            "secondary_keyword_intents": [{"label": "transactional", "probability": 0.25}],
        }]}]
        with patch("aitools.seo.labs.client.post", return_value=_task(result)) as mock_post:
            out = labs.search_intent(["daily planner"], language="en")
        _, payload = mock_post.call_args[0]
        assert "location_code" not in payload[0]  # intent is language-only
        row = out["keywords"][0]
        assert row["intent"] == "informational"
        assert row["secondary_intents"][0]["label"] == "transactional"


# ---------------------------------------------------------------------------
# backlinks
# ---------------------------------------------------------------------------

class TestBacklinks:
    def test_summary_parses_rank(self):
        result = [{
            "target": "todoist.com", "rank": 461, "backlinks": 350242,
            "referring_domains": 33838, "referring_main_domains": 31458,
            "referring_pages": 309143, "backlinks_spam_score": 27,
            "broken_backlinks": 809, "first_seen": "2019-01-15",
        }]
        with patch("aitools.seo.backlinks.client.post", return_value=_task(result)):
            out = backlinks.summary("todoist.com")
        assert out["rank"] == 461
        assert out["backlinks"] == 350242
        assert out["referring_domains"] == 33838

    def test_referring_domains_parses_and_orders(self):
        result = [{"target": "todoist.com", "total_count": 31478, "items": [
            {"domain": "doist.com", "rank": 372, "backlinks": 1904, "backlinks_spam_score": 0, "first_seen": "x"},
        ]}]
        with patch("aitools.seo.backlinks.client.post", return_value=_task(result)) as mock_post:
            out = backlinks.referring_domains("todoist.com", limit=5)
        _, payload = mock_post.call_args[0]
        assert payload[0]["order_by"] == ["rank,desc"]
        assert payload[0]["limit"] == 5
        assert out["domains"][0]["domain"] == "doist.com"
        assert out["domains"][0]["spam_score"] == 0


# ---------------------------------------------------------------------------
# ai_optim
# ---------------------------------------------------------------------------

class TestAiOptim:
    def test_ai_answer_joins_text_sections(self):
        result = [{
            "model_name": "gpt-4o-mini-2024-07-18",
            "input_tokens": 22, "output_tokens": 150, "money_spent": 0.0001,
            "web_search": False,
            "items": [{"type": "message", "sections": [
                {"type": "text", "text": "Part one."},
                {"type": "text", "text": "Part two."},
            ]}],
        }]
        with patch("aitools.seo.ai_optim.client.post", return_value=_task(result)) as mock_post:
            out = ai_optim.ai_answer("best planner", model_name="gpt-4o-mini", web_search=False)
        path, payload = mock_post.call_args[0]
        assert path == "ai_optimization/chat_gpt/llm_responses/live"
        assert payload[0]["user_prompt"] == "best planner"
        assert out["answer"] == "Part one.\n\nPart two."
        assert out["input_tokens"] == 22

    def test_ai_answer_rejects_empty_prompt(self):
        with pytest.raises(ValueError, match="No prompt"):
            ai_optim.ai_answer("")

    def test_ai_search_volume_parses(self):
        result = [{"items": [{"keyword": "daily planner", "ai_search_volume": 1038}]}]
        with patch("aitools.seo.ai_optim.client.post", return_value=_task(result)):
            out = ai_optim.ai_search_volume(["daily planner"], country="us", language="en")
        assert out["keywords"][0]["ai_search_volume"] == 1038


# ---------------------------------------------------------------------------
# onpage
# ---------------------------------------------------------------------------

class TestOnPage:
    def test_instant_page_parses_meta(self):
        result = [{"items": [{
            "url": "https://getsalta.app/", "status_code": 200, "onpage_score": 98.17,
            "meta": {
                "title": "Salta", "description": "desc", "canonical": "https://getsalta.app/",
                "htags": {"h1": ["Hello"]}, "internal_links_count": 15,
                "external_links_count": 7, "images_count": 5,
            },
            "checks": {"title_too_short": True, "no_favicon": False},
        }]}]
        with patch("aitools.seo.onpage.client.post", return_value=_task(result)):
            out = onpage.instant_page("https://getsalta.app")
        assert out["success"] is True
        assert out["title"] == "Salta"
        assert out["h1"] == ["Hello"]
        assert out["onpage_score"] == 98.17
        assert out["checks"]["title_too_short"] is True

    def test_instant_page_no_items_returns_error(self):
        result = [{"items": []}]
        with patch("aitools.seo.onpage.client.post", return_value=_task(result)):
            out = onpage.instant_page("https://unreachable.example")
        assert out["success"] is False
        assert "error" in out
