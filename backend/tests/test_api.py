import importlib

from fastapi.testclient import TestClient


def client(tmp_path, monkeypatch):
    monkeypatch.setenv('VASP_DB_PATH', str(tmp_path / 'cases.sqlite3'))
    monkeypatch.setenv('VASP_MODE', 'fixture')
    from backend import main
    importlib.reload(main)
    return TestClient(main.app), main


def test_trace_persist_report_and_exports(tmp_path, monkeypatch):
    c, main = client(tmp_path, monkeypatch)
    assert c.get('/api/health').json()['mode'] == 'fixture'
    seed = c.get('/api/examples').json()[1]['address']
    r = c.post('/api/trace', json={'address': seed, 'case_ref': 'T-1', 'max_hops': 3})
    assert r.status_code == 200
    body = r.json()
    assert body['nearest']['confidence'] in ('High', 'Medium', 'Low') and body['network'] == 'Bitcoin'
    assert c.get('/api/cases/' + body['id']).json()['seed'] == seed
    report = c.get('/api/cases/' + body['id'] + '/report').text
    assert 'Why:' in report and 'SYNTHETIC' in report
    assert c.get('/api/cases/' + body['id'] + '/export?format=csv').text.startswith('case_ref')
    assert 'Possible exchange deposit' in c.get('/api/cases/' + body['id'] + '/print').text
    assert 'SAMPLE REQUEST DRAFT' in c.get('/api/cases/' + body['id'] + '/draft').json()['text']
    summary = c.get('/api/summary').json()
    assert summary['total'] == 1 and summary['with_candidates'] == 1


def test_invalid_inputs(tmp_path, monkeypatch):
    c, _ = client(tmp_path, monkeypatch)
    assert c.post('/api/trace', json={'address': '0x' + '1' * 40}).status_code == 422
    assert c.post('/api/trace', json={'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb'}).status_code == 422
    seed = c.get('/api/examples').json()[0]['address']
    assert c.post('/api/trace', json={'address': seed, 'max_hops': 9}).status_code == 422
    assert c.post('/api/trace', json={'address': seed, 'network': 'ethereum-demo'}).status_code == 422
    assert c.post('/api/trace', json={'address': seed, 'start': '2026-10-02T00:00:00', 'end': None}).status_code == 422


def test_valid_address_outside_fixture_is_reported_not_found(tmp_path, monkeypatch):
    c, _ = client(tmp_path, monkeypatch)
    r = c.post('/api/trace', json={'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'})
    assert r.status_code == 200 and r.json()['status'] == 'not_in_demo' and r.json()['candidates'] == []


def test_live_mode_traces_a_mainnet_address_through_esplora(tmp_path, monkeypatch):
    monkeypatch.setenv('VASP_DB_PATH', str(tmp_path / 'cases.sqlite3'))
    monkeypatch.setenv('VASP_MODE', 'live')
    monkeypatch.setenv('VASP_ESPLORA_URL', 'https://api.test')
    from backend import main
    importlib.reload(main)

    calls = []
    main.PROVIDER = main.EsploraProvider('https://api.test', fetch=lambda url: calls.append(url) or [], pause=0)
    c = TestClient(main.app)

    assert c.get('/api/health').json()['mode'] == 'live'
    response = c.post('/api/trace', json={'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'})
    assert response.status_code == 200
    assert response.json()['status'] == 'no_activity'
    assert response.json()['mode'] == 'esplora'
    assert calls == ['https://api.test/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa/txs']


def test_review_notes_and_directory(tmp_path, monkeypatch):
    c, _ = client(tmp_path, monkeypatch)
    seed = c.get('/api/examples').json()[0]['address']
    case = c.post('/api/trace', json={'address': seed}).json()
    updated = c.patch('/api/cases/' + case['id'], json={'notes': 'checked', 'review_status': 'reviewed'}).json()
    assert updated['notes'] == 'checked' and updated['review_status'] == 'reviewed'
    assert len(c.get('/api/cases?review=reviewed').json()) == 1
    assert len(c.get('/api/directory').json()) == 3
    assert c.get('/api/cases/missing/draft').status_code == 404
