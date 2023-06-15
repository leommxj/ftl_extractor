import argparse
import logging
import struct
from construct import Struct, Int8ul, Int32ul, Int16ul, Bytes


UnitHeader = Struct(
    "formatPattern" / Bytes(15),
    "noOfTransferUnits" / Int8ul,
    "wearLevelingInfo" / Int32ul,
    "logicalUnitNo" / Int16ul,
    "log2SectorSize" / Int8ul,
    "log2UnitSize" / Int8ul,
    "firstPhysicalEUN" / Int16ul,
    "noOfUnits" / Int16ul,
    "virtualMediumSize" / Int32ul,
    "directAddressingMemory" / Int32ul,
    "noOfPages" / Int16ul,
    "flags" / Int8ul,
    "eccCode" / Int8ul,
    "serialNumber" / Int32ul,
    "altEUHoffset" / Int32ul,
    "BAMoffset" / Int32ul,
    "reversed" / Bytes(12),
    "embeddedCIS" / Bytes(4),
)


def find_unitHeader(data, start):
    # TODO: first 4 bytes may be earsed? should ignore or not?
    r = data.find(b"\x13\x03CISF", start)
    while r >= 0:
        if data[r + 6] == 0xFF:  # TPL_LINK
            if data[r + 7 : r + 7 + 8] == b"\x00FTL100\x00":
                return r
        elif data[r + 6] == 57:
            # in code
            pass
        start = r + 7
        r = data.find(b"\x13\x03CISF", start)
    return r


class Unit:
    def __init__(self, data, uh):
        self.unitData = data
        self.uh = uh
        self.unitNo = uh.logicalUnitNo
        self.unitSize = 1 << uh.log2UnitSize
        self.sectorSize = 1 << uh.log2SectorSize
        self.mapped_data = {}
        self.parse()

    def parse_BamItem(self, v):
        logging.debug("bam item value:{:08x}".format(v))
        if v in (0xFFFFFFFF,):
            # Free Block
            pass
        elif v in (0x0, 0xFFFFFFFE):
            # Deleted Block
            pass
        elif v in (0x30,):
            # Control Block
            pass
        elif v in (0x70,):
            # Bad Block
            pass
        elif (v & 0xFF) == 0x40:
            # Data or Map Page
            addr = v & 0xFFFFFF00
            return addr
        elif (v & 0xFF) == 0x60:
            # Replacement Map page
            # TODO
            pass

        return None

    def parse(self):
        boff = self.uh.BAMoffset
        logging.info("BAMoffset: {} for unitNo: {}".format(boff, self.uh.logicalUnitNo))

        num = int(self.unitSize / self.sectorSize)
        for idx in range(0, num):
            ioff = boff + idx * 4

            sector_f = struct.unpack("<I", self.unitData[ioff : ioff + 4])[0]
            addr = self.parse_BamItem(sector_f)
            if addr is not None:
                if addr in self.mapped_data:
                    logging.warning("same addr parsed?? addr:{:08x}".format(addr))
                self.mapped_data[addr] = self.unitData[
                    idx * self.sectorSize : (idx + 1) * self.sectorSize
                ]


class Vol:
    def __init__(self):
        self.units = {}

    def add_unit(self, unit):
        if unit.unitNo in self.units:
            logging.warning("same unitNo ? unitNo:0x{:04x}".format(unit.unitNo))
        self.units[unit.unitNo] = unit

    def __len__(self):
        return len(self.units)

    def gen_mapped_data(self):
        r = {}
        for unitNo in self.units:
            unit = self.units[unitNo]
            if r.keys() & unit.mapped_data.keys():
                logging.warning("same mapping address? unitNo:{}".format(unit.unitNo))
            r.update(unit.mapped_data)
        return r


def main(args):
    with open(args.filename, "rb") as f:
        data = f.read()

    vol = Vol()
    r = 0
    mediumSize = 0
    while r >= 0:
        r = find_unitHeader(data, r)
        if r < 0:
            break
        uh = UnitHeader.parse(data[r : r + UnitHeader.sizeof()])
        unitSize = 1 << uh.log2UnitSize
        mediumSize = uh.virtualMediumSize
        vol.add_unit(Unit(data[r : r + unitSize], uh))
        r = r + 1
    print("total unit num: {}".format(len(vol)))
    mapped_data = vol.gen_mapped_data()
    print("writing to {}".format(args.outpath))
    with open(args.outpath, "wb") as out:
        out.write(bytes(mediumSize))
        for addr in sorted(mapped_data):
            if addr > mediumSize:
                logging.info(
                    "high virtual address in mapped data: 0x{:08x}, pass".format(addr)
                )
                continue
            out.seek(addr)
            logging.debug("writing 0x{:08x}".format(addr))
            out.write(mapped_data[addr])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="ftl_extractor.py",
        description="extract FTL vol",
    )
    parser.add_argument("filename", help="input file's path (eg.dump from nand)")
    parser.add_argument("outpath", help="output file")
    parser.add_argument("--verbose", "-v", action="count", default=1, help="log level")

    args = parser.parse_args()

    args.verbose = 40 - (10 * args.verbose) if args.verbose > 0 else 0
    logging.basicConfig(
        level=args.verbose,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main(args)
