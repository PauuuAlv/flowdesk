import unittest
from datetime import date
from decimal import Decimal

from app.services.data_transfer import (
    ACTIVITY_TYPES, ENTITIES, PRODUCT_COLUMNS, FileError, Row, RowError, STATUSES, read_csv, write_csv,
)


class DataTransferCsvTests(unittest.TestCase):
    def test_export_has_bom_and_headers(self):
        content = write_csv(PRODUCT_COLUMNS, [{"codigo": "PRO-1", "nombre": "Cámara"}])
        self.assertTrue(content.startswith("﻿".encode("utf-8")))
        self.assertIn("Cámara", content.decode("utf-8-sig"))

    def test_reads_semicolon_and_descriptive_headers(self):
        text = "Código;Nombre;Unidad de medida;Precio base\nPRO-1;Cámara;Pieza;1,250.50\n"
        rows = read_csv(text.encode("utf-8"), PRODUCT_COLUMNS, ("nombre", "unidad"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].number, 2)
        self.assertEqual(rows[0].values["unidad"], "Pieza")
        self.assertEqual(rows[0].decimal("precio_base", "Precio base"), Decimal("1250.50"))

    def test_missing_required_columns(self):
        with self.assertRaises(FileError):
            read_csv(b"codigo,precio_base\nX,1\n", PRODUCT_COLUMNS, ("nombre", "unidad"))

    def test_value_parsers(self):
        row = Row(2, {"a": "199,9", "b": "Sí", "c": "inactivo", "d": "Reunión", "e": "31/12/2026", "f": "abc"})
        self.assertEqual(row.decimal("a", "A"), Decimal("199.90"))
        self.assertTrue(row.boolean("b", "B", False))
        self.assertEqual(row.choice("c", "C", STATUSES), "inactive")
        self.assertEqual(row.choice("d", "D", ACTIVITY_TYPES), "meeting")
        self.assertEqual(row.date("e", "E"), date(2026, 12, 31))
        with self.assertRaises(RowError):
            row.decimal("f", "F")

    def test_entities_import_in_dependency_order(self):
        keys = list(ENTITIES)
        self.assertLess(keys.index("units"), keys.index("products"))
        self.assertLess(keys.index("clients"), keys.index("opportunities"))
        self.assertLess(keys.index("opportunities"), keys.index("activities"))
        self.assertLess(keys.index("opportunities"), keys.index("quotes"))


if __name__ == "__main__":
    unittest.main()
