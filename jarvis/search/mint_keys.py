"""Mint restricted Elastic API keys per role from the master key (segregation of duties in Elastic itself).

    python -m jarvis.search.mint_keys          # prints KEY=VALUE lines to paste into .env

The preparer can read sources and write proposals/audit (create-only), never delete or overwrite audit.
"""
from __future__ import annotations

from elasticsearch import Elasticsearch

from jarvis import config

P = config.ELASTIC_PREFIX

ROLE_DESCRIPTORS = {
    "JARVIS_PREPARER_KEY": {"jarvis_preparer": {"indices": [
        {"names": [f"{P}-docs", f"{P}-precedents", f"{P}-records", f"{P}-vendors", f"{P}-policys"],
         "privileges": ["read", "view_index_metadata", "write"]},
        {"names": [f"{P}-audits"], "privileges": ["create_doc", "read"]}]}},
    "JARVIS_REVIEWER_KEY": {"jarvis_reviewer": {"indices": [
        {"names": [f"{P}-*"], "privileges": ["read"]},
        {"names": [f"{P}-audits"], "privileges": ["create_doc"]}]}},
    "GATEWAY_KEY": {"jarvis_gateway": {"indices": [
        {"names": [f"{P}-records", f"{P}-vendors"], "privileges": ["read", "write"]},
        {"names": [f"{P}-audits"], "privileges": ["create_doc", "read"]}]}},
    "CONTROLLER_KEY": {"jarvis_controller": {"indices": [{"names": [f"{P}-*"], "privileges": ["read"]}]}},
}


def main():
    if not (config.ELASTIC_URL and config.ELASTIC_API_KEY):
        raise SystemExit("Set ELASTIC_URL and ELASTIC_API_KEY in .env first")
    es = Elasticsearch(config.ELASTIC_URL, api_key=config.ELASTIC_API_KEY)
    me = es.security.authenticate()
    print(f"# authenticated as {me.get('username')} via {me.get('authentication_type')}")
    for env_name, rd in ROLE_DESCRIPTORS.items():
        try:
            k = es.security.create_api_key(name=f"jarvis-{env_name.lower()}", role_descriptors=rd, expiration="7d")
            print(f"{env_name}={k['encoded']}")
        except Exception as e:
            print(f"# could not mint {env_name}: {e}")


if __name__ == "__main__":
    main()
