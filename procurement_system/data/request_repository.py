import sqlite3

from intake_management import OrderLine, ProcurementRequest, RequestStatus
from .database_manager import DatabaseManager


class RequestRepository:
    """Repository for saving and loading procurement requests and order lines."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def save_request(self, request: ProcurementRequest) -> int:
        """Save a procurement request and its order lines. Returns the request ID."""
        cursor = self.db_manager.execute(
            """
            INSERT INTO requests (
                requestor_name, title, vendor_name, vat_id,
                requestor_department, commodity_group, total_cost, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.requestor_name,
                request.title,
                request.vendor_name,
                request.vat_id,
                request.requestor_department,
                request.commodity_group,
                request.total_cost,
                request.status.value,
            ),
        )
        request_id = cursor.lastrowid

        self._save_order_lines(request_id, request.order_lines)
        self.db_manager.commit()

        return request_id

    def _save_order_lines(self, request_id: int, order_lines: list[OrderLine]) -> None:
        """Save order lines for a request."""
        params_list = [
            (
                request_id,
                line.position_description,
                line.unit,
                line.unit_price,
                line.amount,
                line.total_price,
            )
            for line in order_lines
        ]

        self.db_manager.execute_many(
            """
            INSERT INTO order_lines (
                request_id, position_description, unit, unit_price, amount, total_price
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            params_list,
        )

    def load_request(self, request_id: int) -> ProcurementRequest | None:
        """Load a procurement request by ID."""
        row = self.db_manager.fetch_one(
            "SELECT * FROM requests WHERE id = ?",
            (request_id,),
        )

        if row is None:
            return None

        order_lines = self._load_order_lines(request_id)
        return self._map_row_to_request(row, order_lines)

    def _load_order_lines(self, request_id: int) -> list[OrderLine]:
        """Load order lines for a request."""
        rows = self.db_manager.fetch_all(
            "SELECT * FROM order_lines WHERE request_id = ?",
            (request_id,),
        )
        return [self._map_row_to_order_line(row) for row in rows]

    def load_all_requests(self) -> list[tuple[int, ProcurementRequest]]:
        """Load all procurement requests. Returns list of (id, request) tuples."""
        rows = self.db_manager.fetch_all("SELECT * FROM requests ORDER BY created_at DESC")
        results = []

        for row in rows:
            order_lines = self._load_order_lines(row["id"])
            request = self._map_row_to_request(row, order_lines)
            results.append((row["id"], request))

        return results

    def load_requests_by_user(self, requestor_name: str) -> list[tuple[int, ProcurementRequest]]:
        """Load all requests for a specific user. Returns list of (id, request) tuples."""
        rows = self.db_manager.fetch_all(
            "SELECT * FROM requests WHERE requestor_name = ? ORDER BY created_at DESC",
            (requestor_name,),
        )
        results = []

        for row in rows:
            order_lines = self._load_order_lines(row["id"])
            request = self._map_row_to_request(row, order_lines)
            results.append((row["id"], request))

        return results

    def delete_request(self, request_id: int) -> bool:
        """Delete a request by ID. Returns True if deleted."""
        cursor = self.db_manager.execute(
            "DELETE FROM requests WHERE id = ?",
            (request_id,),
        )
        self.db_manager.commit()
        return cursor.rowcount > 0

    def update_status(self, request_id: int, status: RequestStatus) -> bool:
        """Update the status of a request. Returns True if updated."""
        cursor = self.db_manager.execute(
            "UPDATE requests SET status = ? WHERE id = ?",
            (status.value, request_id),
        )
        self.db_manager.commit()
        return cursor.rowcount > 0

    def _map_row_to_request(
        self, row: sqlite3.Row, order_lines: list[OrderLine]
    ) -> ProcurementRequest:
        """Map a database row to a ProcurementRequest object."""
        return ProcurementRequest(
            requestor_name=row["requestor_name"],
            title=row["title"],
            vendor_name=row["vendor_name"],
            vat_id=row["vat_id"],
            requestor_department=row["requestor_department"],
            commodity_group=row["commodity_group"],
            total_cost=row["total_cost"],
            order_lines=order_lines,
            status=RequestStatus(row["status"]),
        )

    def _map_row_to_order_line(self, row: sqlite3.Row) -> OrderLine:
        """Map a database row to an OrderLine object."""
        return OrderLine(
            position_description=row["position_description"],
            unit=row["unit"],
            unit_price=row["unit_price"],
            amount=row["amount"],
            total_price=row["total_price"],
        )
