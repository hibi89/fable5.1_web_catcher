"""Step 3 Record input, sanitization and candidate regression (offline)."""
import pytest

from scanner.record_scan import allowed_origins, record_safe_url
from scanner.chart_mapping import map_chart_api_candidates


def test_record_url_drops_query_fragment_credentials_and_dynamic_path():
    url = 'https://u:p@example.com/api/orders/user@email.com/ABC123456?name=REAL_PERSON&token=SECRET#form'
    redacted = record_safe_url(url)
    assert redacted.startswith('https://example.com/api/orders/')
    for secret in ('u:p', 'user@email', 'ABC123456', 'REAL_PERSON', 'SECRET', 'form'):
        assert secret not in redacted
    assert '[REDACTED]' in redacted


def test_explicit_origin_rules_never_accept_wildcards_or_path():
    assert allowed_origins('https://example.com/path', ['http://127.0.0.1:8000']) == {
        'https://example.com', 'http://127.0.0.1:8000'}
    for value in ('*', 'https://*.example.com', 'https://example.com/path',
                  'https://example.com/?token=secret', 'file:///etc/passwd'):
        with pytest.raises(ValueError):
            allowed_origins('https://example.com', [value])


def test_record_mappings_require_same_document_and_do_not_infer_causality():
    chart = {
        'id': 'page-001-nav-0001-chart-001', 'page_id': 'page-001',
        'navigation_id': 'nav-0001', 'library': 'Highcharts',
        'detection_level': 'library_dom_candidate',
        'library_evidence': ['highcharts_dom_marker'],
        'last_observed_update_ms': 2000, 'data_sources': [],
    }
    api = {
        'id': 'api-0001', 'page_id': 'page-002', 'navigation_id': 'nav-0001',
        'request_started_at_ms': 1200, 'response_received_at_ms': 1600,
        'status': 200, 'response_body_analysis': 'structure_only',
        'json_structure': {'items': [{'date': 'string', 'value': 'number'}]},
    }
    data = {'scan_mode': 'record', 'charts': [chart], 'api': {'endpoints': [api]},
            'runtime': {}, 'record': {'interactions': []}}
    map_chart_api_candidates(data)
    assert data['api']['chart_candidates'] == []
    api['page_id'] = 'page-001'
    map_chart_api_candidates(data)
    assert len(data['api']['chart_candidates']) == 1
    assert 'preceding_manual_interaction_marker' not in data['api']['chart_candidates'][0]['reasons']
    data['record']['interactions'] = [{'page_id': 'page-001', 'navigation_id': 'nav-0001',
                                       'at_ms': 1000}]
    map_chart_api_candidates(data)
    link = data['api']['chart_candidates'][0]
    assert 'preceding_manual_interaction_marker' in link['reasons']
    assert 'interaction_does_not_prove_causality' in link['limitations']
