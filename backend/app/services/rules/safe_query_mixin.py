from sqlalchemy import text
from typing import Set, Dict

class SafeQueryMixin:
    """
    Mixin to provide safe data retrieval methods that check schema availability.
    """
    _schema_cache: Dict[str, Set[str]] = {}

    def _ensure_schema_loaded(self, table_name: str):
        if table_name in self._schema_cache:
            return
            
        try:
            # Get column names
            query = text(f"SELECT * FROM {table_name} LIMIT 0")
            result = self.db.execute(query)
            self._schema_cache[table_name] = set(result.keys())
        except Exception as e:
            print(f"Error loading schema for {table_name}: {e}")
            self._schema_cache[table_name] = set()

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        self._ensure_schema_loaded(table_name)
        return column_name in self._schema_cache[table_name]

    def _safe_get_value(self, table_name: str, column_name: str, params: dict, default=0.0):
        if not self._column_exists(table_name, column_name):
            # print(f"WARNING: Column {column_name} missing in {table_name}. Using default {default}")
            return default
            
        query = text(f"SELECT {column_name} FROM {table_name} WHERE property_id = :p_id AND period_id = :period_id LIMIT 1")
        try:
            val = self.db.execute(query, params).scalar()
            return float(val) if val is not None else default
        except Exception as e:
            print(f"Error Safe Query {table_name}.{column_name}: {e}")
            return default
