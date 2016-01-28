# -*- encoding: utf-8 -*-
#
# Authors: Asger Anders Lund Hansen, Mads Ynddal and Troels Ynddal
# License: See LICENSE file
# GitHub: https://github.com/Baekalfen/PyBoy
#

import struct
import CoreDump
import random
import math

# RAM SIZES
# 16KB ROM bank #0
# 16KB switchable ROM bank
VIDEO_RAM = 8 * 1024  # 8KB
# 8KB switchable RAM bank
INTERNAL_RAM_0 = 8 * 1024  # 8KB
# Echo of internal RAM
SPRITE_ATTRIB_MEMORY = 0xA0
NON_IO_INTERNAL_RAM0 = 0x60
IO_PORTS = 0x4C
NON_IO_INTERNAL_RAM1 = 0x34
INTERNAL_RAM_1 = 0x7F
INTERRUPT_ENABLE_REGISTER = 1
##


class RAM():

    def __init__(self, bootROMFile, cartridge, interaction, timer, random=False): #NOTE: In real life, the RAM is scrambled with random data on boot.
        if random:
            raise Exception("Random RAM not implemented")

        if bootROMFile is not None:
            with open(bootROMFile, "rb") as bootROMFileHandle:
                self.bootROM = [struct.unpack('B', byte)[0]
                                for byte in bootROMFileHandle.read()]
        else:
            self.bootROM = self.allocateRAM(256)
            # Set stack pointer
            self.bootROM[0x00] = 0x31
            self.bootROM[0x01] = 0xFE
            self.bootROM[0x02] = 0xFF

            # Inject jump to 0xFC
            self.bootROM[0x03] = 0xC3
            self.bootROM[0x04] = 0xFC
            self.bootROM[0x05] = 0x00

            # Inject code to disable boot-ROM
            self.bootROM[0xFC] = 0x3E
            self.bootROM[0xFD] = 0x01
            self.bootROM[0xFE] = 0xE0
            self.bootROM[0xFF] = 0x50

        self.bootROMEnabled = True

        self.cartridge = cartridge
        self.interaction = interaction
        self.timer = timer
        self.updateVRAMCache = True
        self.videoRAM = self.allocateRAM(VIDEO_RAM)
        self.internalRAM0 = self.allocateRAM(INTERNAL_RAM_0)
        self.spriteAttributeMemory = self.allocateRAM(SPRITE_ATTRIB_MEMORY)
        self.nonIOInternalRAM0 = self.allocateRAM(NON_IO_INTERNAL_RAM0)
        self.IOPorts = self.allocateRAM(IO_PORTS)
        self.internalRAM1 = self.allocateRAM(INTERNAL_RAM_1)
        self.nonIOInternalRAM1 = self.allocateRAM(NON_IO_INTERNAL_RAM1)
        self.interruptRegister = self.allocateRAM(INTERRUPT_ENABLE_REGISTER)

    def allocateRAM(self, size, rand=False):
        if rand:
            # return [random.randrange(0x00,0xFF) for x in range(size)]
            raise Exception("Random RAM not implemented")

        return [0 for x in range(size)]

    def listToHex(self,a,compress = True, offset=0):
        output = "%s00%s08%s0F\n" % (" "*7," "*(22)," "*(19))

        bytesPerRow = 16
        getSlice = lambda a,x: a[x*bytesPerRow:min(len(a),(x+1)*bytesPerRow)]
        prevWasZero = False

        # Rounding up trick. 0x34 -> 0x40. 0xFF -> 0xFF.
        # To not miss last not bytesPerRow-divisible bytes
        for n in range((len(a)+(bytesPerRow-1))/bytesPerRow):
            currentSlice = getSlice(a,n)

            if compress and (n == ((len(a)+(bytesPerRow-1))/bytesPerRow)-1) and prevWasZero:
                output += " ... \n"
                pass
            elif compress and sum(currentSlice) == 0 and prevWasZero:
                continue
            elif compress and sum(currentSlice) != 0 and prevWasZero:
                output += " ... \n"


            output += "0x%0*X " % (4,(n*bytesPerRow)+offset)
            output += " ".join(["%0*X" % (2,x) for x in currentSlice])
            output += "\n"

            prevWasZero = (sum(currentSlice) == 0)

        return output

    def dump(self):
        dump = "Dump of ROM:\n"
        dump += "self.bootROMEnabled: " + str(self.bootROMEnabled) + "\n"
        dump += "self.bootROM:\n"
        dump += self.listToHex(self.bootROM) + "\n"
        dump += "self.cartridge:\n"
        dump += str(self.cartridge) + "\n"
        dump += "self.cartridge.ROMBanks\n"
        for i,bank in enumerate(self.cartridge.ROMBanks):
            dump += "Bank: %s" % i
            dump += self.listToHex(bank,offset=i*16*1024) + "\n" #Offset of 16KB
        dump += "self.interaction:\n"
        dump += str(self.interaction) + "\n"
        dump += "self.videoRAM:\n"
        dump += self.listToHex(self.videoRAM) + "\n"
        dump += "self.internalRAM0:\n"
        dump += self.listToHex(self.internalRAM0) + "\n"
        dump += "self.spriteAttributeMemory:\n"
        dump += self.listToHex(self.spriteAttributeMemory) + "\n"
        dump += "self.nonIOInternalRAM0:\n"
        dump += self.listToHex(self.nonIOInternalRAM0) + "\n"
        dump += "self.IOPorts:\n"
        dump += self.listToHex(self.IOPorts) + "\n"
        dump += "self.internalRAM1:\n"
        dump += self.listToHex(self.internalRAM1) + "\n"
        dump += "self.nonIOInternalRAM1:\n"
        dump += self.listToHex(self.nonIOInternalRAM1) + "\n"
        dump += "self.interruptRegister:\n"
        dump += self.listToHex(self.interruptRegister) + "\n"

        return dump

    def __getitem__(self, i):
        if 0x0000 <= i < 0x4000:  # 16kB ROM bank #0
            if i <= 0xFF and self.bootROMEnabled:
                return self.bootROM[i]
            else:
                return self.cartridge[i]
        elif 0x4000 <= i < 0x8000:  # 16kB switchable ROM bank
            return self.cartridge[i]
        elif 0x8000 <= i < 0xA000:  # 8kB Video RAM
            return self.videoRAM[i - 0x8000]
        elif 0xA000 <= i < 0xC000:  # 8kB switchable RAM bank
            return self.cartridge[i]
        elif 0xC000 <= i < 0xE000:  # 8kB Internal RAM
            return self.internalRAM0[i - 0xC000]
        elif 0xE000 <= i < 0xFE00:  # Echo of 8kB Internal RAM
            # Redirect to internal RAM
            return self[i - 0x2000]
        elif 0xFE00 <= i < 0xFEA0:  # Sprite Attrib Memory (OAM)
            # print "OAM! read",hex(i),self.spriteAttributeMemory[i - 0xFE00]
            return self.spriteAttributeMemory[i - 0xFE00]
        elif 0xFEA0 <= i < 0xFF00:  # Empty but unusable for I/O
            return self.nonIOInternalRAM0[i - 0xFEA0]
        elif 0xFF00 <= i < 0xFF4C:  # I/O ports
            if i == 0xFF04:
                # http://problemkaputt.de/pandocs.htm#timeranddividerregisters
                # print "get DIV",
                return self.timer.DIV
            elif i == 0xFF05:
                # print "get TIMA"
                return self.timer.TIMA
            elif i == 0xFF06:
                # print "get TMA"
                return self.timer.TMA
            elif i == 0xFF07:
                # print "get TAC"
                return self.timer.TAC
            return self.IOPorts[i - 0xFF00]
        elif 0xFF4C <= i < 0xFF80:  # Empty but unusable for I/O
            return self.nonIOInternalRAM1[i - 0xFF4C]
        elif 0xFF80 <= i < 0xFFFF:  # Internal RAM
            return self.internalRAM1[i-0xFF80]
        elif i == 0xFFFF:  # Interrupt Enable Register
            return self.interruptRegister[0]
        raise CoreDump.CoreDump("Memory access violation. Tried to accessed: %s" % hex(i))

    def __setitem__(self,i,value):
        if value > 0x100:
            print "Memory write error! Can't write %s to %s" % (hex(value),hex(i))
            CoreDump.CoreDump("Memory write error! Can't write %s to %s" % (hex(value),hex(i)))
            exit(1)

        if 0x0000 <= i < 0x4000:  # 16kB ROM bank #0
            self.cartridge[i] = value #Doesn't change the data. This is for MBC commands
        elif 0x4000 <= i < 0x8000:  # 16kB switchable ROM bank
            self.cartridge[i] = value #Doesn't change the data. This is for MBC commands
        elif 0x8000 <= i < 0xA000:  # 8kB Video RAM
            # TODO: Set a flag for when the Video RAM has changed. This can be used for caching the tile data/view
            if i < 0x9800:
                self.updateVRAMCache = True
            self.videoRAM[i - 0x8000] = value
        elif 0xA000 <= i < 0xC000:  # 8kB switchable RAM bank
            self.cartridge[i] = value
        elif 0xC000 <= i < 0xE000:  # 8kB Internal RAM
            self.internalRAM0[i - 0xC000] = value
        elif 0xE000 <= i < 0xFE00:  # Echo of 8kB Internal RAM
            # Redirect to internal RAM
            self[i - 0x2000] = value
        elif 0xFE00 <= i < 0xFEA0:  # Sprite Attrib Memory (OAM)
            # if value != 0:
            #     print "OAM! write",hex(i),hex(value)
            self.spriteAttributeMemory[i - 0xFE00] = value
        elif 0xFEA0 <= i < 0xFF00:  # Empty but unusable for I/O
            self.nonIOInternalRAM0[i - 0xFEA0] = value
        elif 0xFF00 <= i < 0xFF4C:  # I/O ports
            if i == 0xFF00:
                self.IOPorts[i - 0xFF00] = self.interaction.pull(value)
            elif i == 0xFF04:
                # print "DIV", hex(value)
                # http://problemkaputt.de/pandocs.htm#timeranddividerregisters
                # "Writing any value to this register resets it to 00h."
                self.timer.DIV = 0
            elif i == 0xFF05:
                # print "TIMA", hex(value)
                self.timer.TIMA = value
            elif i == 0xFF06:
                # print "TMA", hex(value)
                self.timer.TMA = value
            elif i == 0xFF07:
                # print "TAC", hex(value)
                self.timer.TAC = value
            else:
                if i == 0xFF46:
                    # print "DMA transfer :",hex(i),"value:",hex(value)
                    self.transferDMAtoOAM(value)
                self.IOPorts[i - 0xFF00] = value
        elif 0xFF4C <= i < 0xFF80:  # Empty but unusable for I/O
            if self.bootROMEnabled and i == 0xFF50 and value == 1:
                self.bootROMEnabled = False
            self.nonIOInternalRAM1[i - 0xFF4C] = value
        elif 0xFF80 <= i < 0xFFFF:  # Internal RAM
            # if i == 0xFF80:
                # print "Now",hex(i),hex(value)
                # CoreDump.CoreDump(str(hex(value)))
            self.internalRAM1[i-0xFF80] = value
        elif i == 0xFFFF:  # Interrupt Enable Register
            self.interruptRegister[0] = value
        else:
            raise CoreDump.CoreDump("Memory access violation. Tried to accessed: %s" % hex(i))

    def transferDMAtoOAM(self,src,dst=0xFE00):
        # http://problemkaputt.de/pandocs.htm#lcdoamdmatransfers
        # TODO: Add timing delay of 160µs and disallow access to RAM!
        offset = src * 0x100
        for n in xrange(0x00,0xA0):
            self.__setitem__(0xFE00 + n, self.__getitem__(n + offset))

    def __str__(self):
        string = "Memory dump:\n"
        for i in 0xFF:
            for j in 0xFF:
                string += self[j+i]
            string += "\n"
        return string



if __name__ == "__main__":
    ram = RAM(None, None)

    ram[0xFF40] = 123

    print ram[0xFF40]