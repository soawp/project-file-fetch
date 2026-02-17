import os
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

BASE_URL = "https://api.rentman.net"
logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


@dataclass
class RentmanClient:
    """Lightweight client for the Rentman API."""

    token: str
    project: Optional[int] = None
    _headers: dict = field(init=False, repr=False)

    def __post_init__(self):
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_project_equipment(self, project: Optional[int] = None, limit: int = 100) -> list[dict]:
        proj = project or self.project
        if proj is None:
            raise ValueError("No project id provided")

        url = f"{BASE_URL}/projects/{proj}/projectequipment"
        return self._fetch_all_pages(url, limit=limit)

    def get_serial_number_info(self, ids: list[str]) -> list[dict]:
        """
        Fetch serial numbers in batches via ``/serialnumbers?id[]=X&id[]=Y``.
        Uses small batches to avoid URI-too-long errors.
        """
        if not ids:
            logger.info("No serial-number ids to fetch.")
            return []

        all_details: list[dict] = []
        total_batches = (len(ids) + _BATCH_SIZE - 1) // _BATCH_SIZE

        for batch_num, start in enumerate(range(0, len(ids), _BATCH_SIZE), 1):
            batch = ids[start : start + _BATCH_SIZE]
            logger.info(
                "Fetching serial-number batch %d/%d (%d ids)",
                batch_num, total_batches, len(batch),
            )

            url = f"{BASE_URL}/serialnumbers"
            params = {"id": ",".join(batch)}
            resp = requests.get(url, headers=self._headers, params=params)

            if resp.status_code == 404:
                logger.warning("Batch %d returned 404, skipping.", batch_num)
                continue
            if not resp.ok:
                logger.error(
                    "HTTP %d from %s — %s",
                    resp.status_code, url, resp.text[:500],
                )
                resp.raise_for_status()

            data = resp.json()
            items = self._extract_items(data)
            if isinstance(items, list):
                all_details.extend(items)
            else:
                all_details.append(items)

        logger.info("Fetched details for %d serial numbers.", len(all_details))
        return all_details

    # ------------------------------------------------------------------
    # Extraction helper
    # ------------------------------------------------------------------

    @staticmethod
    def extract_serial_ids(items: list[dict]) -> list[str]:
        candidate_keys = (
            "serial_number_ids",
            "serial_number_id",
            "serialnumber_ids",
            "serialnumber_id",
            "serialnumber",
            "serial_numbers",
            "serial_numbers_ids",
            "id",
        )

        ids: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in candidate_keys:
                val = item.get(key)
                if val is None:
                    continue
                if isinstance(val, str):
                    # Handle comma-separated id strings like "123,456,789"
                    ids.extend(v.strip() for v in val.split(",") if v.strip())
                elif isinstance(val, (list, tuple)):
                    ids.extend(str(v) for v in val if v is not None)
                else:
                    ids.append(str(val))
                break

        seen: set[str] = set()
        out: list[str] = []
        for i in ids:
            if i and i not in seen:
                seen.add(i)
                out.append(i)

        logger.info("Extracted %d unique serial ids from %d items.", len(out), len(items))
        return out

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_all_pages(self, url: str, limit: int = 100) -> list[dict]:
        all_items: list[dict] = []
        offset = 0

        while True:
            params = {"limit": limit, "offset": offset}
            logger.info("GET %s  params=%s", url, params)
            resp = requests.get(url, headers=self._headers, params=params)
            if not resp.ok:
                logger.error(
                    "HTTP %d from %s — %s",
                    resp.status_code, url, resp.text[:500],
                )
                resp.raise_for_status()
            data = resp.json()

            items = self._extract_items(data)
            if not items:
                break

            all_items.extend(items)
            if len(items) < limit:
                break
            offset += limit

        logger.info("Finished paging %s – %d items total.", url, len(all_items))
        return all_items

    @staticmethod
    def _extract_items(data) -> list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "results", "items", "serialnumbers", "rows"):
                if isinstance(data.get(key), list):
                    return data[key]
        return []
