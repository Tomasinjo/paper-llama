import requests
from typing import List, Optional, Dict, Any
from src.config import settings
from src.models import PaperlessDocument
from src.utils import logger
import json

class PaperlessClient:
    def __init__(self):
        self.base_url = settings.paperless_url.rstrip('/')
        self.headers = {
            "Authorization": f"Token {settings.paperless_token}",
            "Accept": "application/json; version=2"
        }

        self._tags_map: Dict[str, int] = {} 
        self._correspondents_map: Dict[str, int] = {}
        self._types_map: Dict[str, int] = {}
        self._processed_cf_id: int = 0
        

    def refresh_metadata(self):
        """Fetch all metadata to map names to IDs."""
        logger.info("Loading metadata, this can take a minute or more..")
        self._tags_map = self._fetch_all_pages("tags")
        self._correspondents_map = self._fetch_all_pages("correspondents")
        self._types_map = self._fetch_all_pages("document_types")
        self._processed_cf_id = self._get_ai_processed_cf_id()
        logger.info(f"Loaded metadata: {len(self._tags_map)} tags, {len(self._correspondents_map)} correspondents.")

    def _fetch_all_pages(self, endpoint: str) -> Dict[str, int]:
        """Helper to get all items from paginated API and map Name -> ID."""
        mapping = {}
        next_url = f"{self.base_url}/api/{endpoint}/"
        while next_url:
            resp = requests.get(next_url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            for item in data['results']:
                mapping[item['name'].lower()] = item['id']
            next_url = data['next']
        return mapping


    def get_document(self, doc_id: int) -> PaperlessDocument:
        resp = requests.get(f"{self.base_url}/api/documents/{doc_id}/", headers=self.headers)
        resp.raise_for_status()
        return PaperlessDocument(**resp.json())

    def get_documents_to_process(self) -> List[PaperlessDocument]:
        """Fetch documents that do NOT have the AI Processed custom field or is false"""
        params = {
            "custom_field_query": json.dumps(["OR",[["AI Processed","exact","false"],["AI Processed","exists","false"]]]),
            "ordering": "-created",
            "page_size": 20 # Process in batches
        }
        resp = requests.get(f"{self.base_url}/api/documents/", headers=self.headers, params=params)
        resp.raise_for_status()
        
        docs = []
        for d in resp.json()['results']:
            docs.append(PaperlessDocument(**d))
        return docs

    def _get_or_create_correspondent(self, name: str) -> Optional[int]:
        if not name: return None
        name_clean = name.strip()
        name_lower = name_clean.lower()
        
        if name_lower in self._correspondents_map:
            return self._correspondents_map[name_lower]
        
        # Create new
        logger.info(f"Creating new correspondent: {name_clean}")
        resp = requests.post(
            f"{self.base_url}/api/correspondents/",
            headers=self.headers,
            json={"name": name_clean}
        )
        if resp.status_code == 201:
            new_id = resp.json()['id']
            self._correspondents_map[name_lower] = new_id
            return new_id
        return None

    def _get_or_create_doctype(self, name: str) -> Optional[int]:
        if not name: return None
        name_clean = name.strip()
        name_lower = name_clean.lower()
        
        if name_lower in self._types_map:
            return self._types_map[name_lower]
        
        # Create new
        logger.info(f"Creating new document type: {name_clean}")
        resp = requests.post(
            f"{self.base_url}/api/document_types/",
            headers=self.headers,
            json={"name": name_clean}
        )
        if resp.status_code == 201:
            new_id = resp.json()['id']
            self._types_map[name_lower] = new_id
            return new_id
        return None
    
    def _get_tag_ids(self, tag_names: List[str]) -> List[int]:
        ids = []
        for name in tag_names:
            name_clean = name.strip()
            name_lower = name_clean.lower()
            if name_lower in self._tags_map:
                ids.append(self._tags_map[name_lower])
            else:
                # Create new tag
                logger.info(f"Creating new tag: {name_clean}")
                resp = requests.post(
                    f"{self.base_url}/api/tags/",
                    headers=self.headers,
                    json={"name": name_clean}
                )
                if resp.status_code == 201:
                    new_id = resp.json()['id']
                    self._tags_map[name_lower] = new_id
                    ids.append(new_id)
        return ids

    def _get_ai_processed_cf_id(self) -> int:
        url = f"{self.base_url}/api/custom_fields/"
        resp = requests.get(url, headers=self.headers, params={"name__iexact": "AI Processed"})
        resp.raise_for_status()
        data = resp.json()
        for item in data['results']:
            if (id_ := item.get('id')) and item.get('data_type') == 'boolean':
                return id_
        logger.warning("Custom field AI Processed was not found, will be created..")
        self._create_custom_field("AI Processed", "boolean")
        return self._get_ai_processed_cf_id()

    def _create_custom_field(self, name: str, data_type: str):
        url = f"{self.base_url}/api/custom_fields/"
        resp = requests.post(url, headers=self.headers, json={"name": name, "data_type": data_type})
        resp.raise_for_status()

    def update_document(self, doc: PaperlessDocument, llm_data: Any):
        """
        Maps LLM strings to IDs and updates the document.
        """
        
        payload = {}
        
        # Map fields
        if llm_data.title:
            payload['title'] = llm_data.title
        
        if llm_data.created:
            payload['created'] = llm_data.created
            
        if llm_data.correspondent:
            c_id = self._get_or_create_correspondent(llm_data.correspondent)
            if c_id: payload['correspondent'] = c_id
            
        if llm_data.document_type:
            dt_id = self._get_or_create_doctype(llm_data.document_type)
            if dt_id: payload['document_type'] = dt_id
            
        # Handle Tags (Merge existing + LLM tags + AI tag)
        new_tag_ids = self._get_tag_ids(llm_data.tags)
        existing_tags = doc.tags if not settings.override_existing_tags else []
        final_tags = list(set(existing_tags + new_tag_ids))
        payload['tags'] = final_tags

        payload['custom_fields'] = [{'field': self._processed_cf_id, 'value': True}]

        logger.info(f"Updating Document {doc.id}...")
        resp = requests.patch(
            f"{self.base_url}/api/documents/{doc.id}/",
            headers=self.headers,
            json=payload
        )
        try:
            resp.raise_for_status()
            logger.info(f"Successfully updated Document {doc.id}")
        except Exception as e:
            logger.error(f"Failed to update document {doc.id}: {resp.text}")
