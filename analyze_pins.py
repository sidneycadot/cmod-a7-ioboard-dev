#! /usr/bin/env python3

import re
from collections import namedtuple

XilinxPinDefinition = namedtuple("XilinxPinDefinition", "pin, pin_name, memory_byte_group, bank, io_type")
XdcPinDefinition = namedtuple("XdcPinDefinition", "pin, io_standard, port_name, pin_name, schematic_name")

def read_xilinx_pindefs(filename):

    pindefs = {}
    with open(filename, "r") as fi:
        fi.readline()
        fi.readline()
        fi.readline()
        for line in fi:
            line = line.rstrip()
            if len(line) == 0:
                break

            (pin, pin_name, memory_byte_group, bank, vccaux_group, super_logic_region, io_type, no_connect) = line.split()

            assert vccaux_group == "NA"
            assert super_logic_region == "NA"
            assert no_connect == "NA"

            pindef = XilinxPinDefinition(pin, pin_name, memory_byte_group, bank, io_type)
            assert pindef.pin not in pindefs
            pindefs[pindef.pin] = pindef

    return pindefs

def read_xdc_pindefs(filename):

    re_pindef = re.compile("#set_property -dict { PACKAGE_PIN ([A-Z][0-9]+) +IOSTANDARD ([A-Z0-9]+) } \[get_ports { ([A-Za-z0-9_\[\]]+) +}\]; #([A-Z0-9_]+) Sch=(.*)$")

    pindefs = {}
    with open(filename, "r") as fi:
        for line in fi:
            m = re_pindef.match(line)
            if m is None:
                continue

            (pin, io_standard, port_name, pin_name, schematic_name) = m.groups()
            schematic_name = schematic_name.replace(" ", "")

            pindef = XdcPinDefinition(pin, io_standard, port_name, pin_name, schematic_name)

            assert pindef.pin not in pindefs
            pindefs[pindef.pin] = pindef

    return pindefs

def peer_pin(name):
    re_pin = re.compile("(IO_L[0-9]+)([PN])(.*)")
    m = re_pin.match(name)
    if m is None:
        return (None, None)
    (prefix, posneg, suffix) = m.groups()
    if posneg == "P":
        other = "N"
    else:
        other = "P"
    return (posneg, prefix + other + suffix)


xilinx_pindefs = read_xilinx_pindefs("xc7a35tcpg236pkg.txt")
xdc_pindefs = read_xdc_pindefs("Cmod-A7-Master.xdc")

for pin1 in xilinx_pindefs.values():
    for pin2 in xdc_pindefs.values():
        if pin1.pin == pin2.pin:
            assert pin1.pin_name == pin2.pin_name

pio_pins = [pin for pin in xdc_pindefs.values() if pin.port_name.startswith("pio")]

assert len(pio_pins) == 44

pio_pairs = []

pio_singles = pio_pins.copy()

while True:
    pair = None
    for i in range(len(pio_singles)):
        (posneg, peer) = peer_pin(pio_singles[i].pin_name)
        if posneg != "P":
            continue
        for j in range(len(pio_singles)):
            if pio_singles[j].pin_name == peer:
                pair = (i, j)
        if pair is not None:
            break
    if pair is None:
        break
    (p, n) = pair
    pio_pairs.append((pio_singles[p], pio_singles[n]))
    del pio_singles[max(p, n)]
    del pio_singles[min(p, n)]

for (pio1, pio2) in pio_pairs:
    if "RCC" in pio1.pin_name:
        cc = "clock-capable"
    else:
        cc = "regular      "
    print("{} differential PIO pair ...... :    {:10} {:20}  /  {:10} {:20}".format(cc, pio1.port_name.upper(), pio1.pin_name, pio2.port_name.upper(), pio2.pin_name))

print()

for pio in pio_singles:
    if "RCC" in pio.pin_name:
        cc = "clock-capable"
    else:
        cc = "regular      "
    print("{} single-ended PIO ........... :    {:10} {:20}".format(cc, pio.port_name.upper(), pio.pin_name))
