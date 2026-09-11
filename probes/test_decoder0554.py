import unittest
from decoder0554 import decode_confirmed, decode_order_id, decode_lots, read_varint, split_chunks

class Decoder0554Tests(unittest.TestCase):
    def test_varint_and_order_xor(self):
        item = read_varint(bytes.fromhex("f6efcb50"))
        self.assertEqual(item.value, -84507638)
        self.assertEqual(decode_order_id(item.value), 26233279)
        item = read_varint(bytes.fromhex("e1e8cb50"))
        self.assertEqual(decode_order_id(item.value), 26232936)

    def test_split_and_confirm_known_payload(self):
        payload = bytes.fromhex(
            "4c496faa4b49ca2e494a49f6efcb50e7ebbe51"
            "ca2e494a49f6efcb50c68ec850"
            "ca2e494849f6efcb50e1e8cb50"
            "ca2e494749c2e3cb50e1e8cb50"
            "ca2e494f49c2e3cb50e0e8cb50"
        )
        header, first, later = split_chunks(payload)
        self.assertEqual(header, (-12, -9, -47, 4842, -9))
        self.assertEqual(len(later), 4)
        self.assertEqual(decode_confirmed(later[0])["lots"], 3)
        self.assertEqual(decode_confirmed(later[1])["lots"], 1)
        self.assertEqual(decode_confirmed(later[2])["lots"], 14)
        self.assertEqual(decode_confirmed(later[2])["bid_order_number"], 26233483)
        self.assertEqual(decode_confirmed(later[2])["ask_order_number"], 26232936)

    def test_lots_xor(self):
        self.assertEqual(decode_lots(-10), 3)
        self.assertEqual(decode_lots(-8), 1)
        self.assertEqual(decode_lots(-7), 14)

if __name__ == "__main__":
    unittest.main()
