"""A tiny MIPS (R5900 subset) assembler with labels, for SRW Impact's code patches.

  a = Asm(origin)
  a.label("loop"); a.lbu("t0", 0, "s1"); a.beqz("t0", "done"); a.nop() ...
  words = a.assemble()       # resolves labels; also accepts absolute int targets

Branch and jump targets may be label names or absolute addresses. No delay-slot magic: every
branch is followed by whatever instruction the caller emits next (usually nop).
"""
REG = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, origin):
        self.origin = origin
        self.items = []          # (kind, args)
        self.labels = {}

    @property
    def pc(self):
        return self.origin + 4 * len(self.items)

    def label(self, name):
        assert name not in self.labels, name
        self.labels[name] = self.pc

    def _emit(self, fn):
        self.items.append(fn)

    def word(self, w):
        self._emit(lambda pc, L: w & 0xFFFFFFFF)

    # ---- encoders
    @staticmethod
    def _r(rs, rt, rd, sa, fn):
        return (REG[rs] << 21) | (REG[rt] << 16) | (REG[rd] << 11) | (sa << 6) | fn

    @staticmethod
    def _i(op, rs, rt, imm):
        return (op << 26) | (REG[rs] << 21) | (REG[rt] << 16) | (imm & 0xFFFF)

    def _target(self, t, L):
        return L[t] if isinstance(t, str) else t

    def _branch(self, op, rs, rt, target, regimm=None):
        def enc(pc, L):
            off = (self._target(target, L) - (pc + 4)) >> 2
            assert -0x8000 <= off < 0x8000, f"branch out of range at {pc:#x}"
            if regimm is not None:
                return (1 << 26) | (REG[rs] << 21) | (regimm << 16) | (off & 0xFFFF)
            return (op << 26) | (REG[rs] << 21) | (REG[rt] << 16) | (off & 0xFFFF)
        self._emit(enc)

    # ---- instructions
    def nop(self): self.word(0)
    def addu(self, rd, rs, rt): self.word(self._r(rs, rt, rd, 0, 0x21))
    def subu(self, rd, rs, rt): self.word(self._r(rs, rt, rd, 0, 0x23))
    def move(self, rd, rs): self.addu(rd, rs, "zero")
    def sll(self, rd, rt, sa): self.word(self._r("zero", rt, rd, sa, 0x00))
    def srl(self, rd, rt, sa): self.word(self._r("zero", rt, rd, sa, 0x02))
    def slt(self, rd, rs, rt): self.word(self._r(rs, rt, rd, 0, 0x2A))
    def sltu(self, rd, rs, rt): self.word(self._r(rs, rt, rd, 0, 0x2B))
    def mult(self, rs, rt): self.word(self._r(rs, rt, "zero", 0, 0x18))
    def mflo(self, rd): self.word(self._r("zero", "zero", rd, 0, 0x12))
    def jr(self, rs): self.word(self._r(rs, "zero", "zero", 0, 0x08))
    def addiu(self, rt, rs, imm): self.word(self._i(0x09, rs, rt, imm))
    def li(self, rt, imm):
        assert -0x8000 <= imm < 0x8000
        self.addiu(rt, "zero", imm)
    def sltiu(self, rt, rs, imm): self.word(self._i(0x0B, rs, rt, imm))
    def andi(self, rt, rs, imm): self.word(self._i(0x0C, rs, rt, imm))
    def ori(self, rt, rs, imm): self.word(self._i(0x0D, rs, rt, imm))
    def lui(self, rt, imm): self.word(self._i(0x0F, "zero", rt, imm))
    def lb(self, rt, off, rs): self.word(self._i(0x20, rs, rt, off))
    def lh(self, rt, off, rs): self.word(self._i(0x21, rs, rt, off))
    def lw(self, rt, off, rs): self.word(self._i(0x23, rs, rt, off))
    def lbu(self, rt, off, rs): self.word(self._i(0x24, rs, rt, off))
    def lhu(self, rt, off, rs): self.word(self._i(0x25, rs, rt, off))
    def sb(self, rt, off, rs): self.word(self._i(0x28, rs, rt, off))
    def sh(self, rt, off, rs): self.word(self._i(0x29, rs, rt, off))
    def sw(self, rt, off, rs): self.word(self._i(0x2B, rs, rt, off))

    def la(self, rt, addr):
        """lui/addiu pair for an absolute address (addiu sign-extends)."""
        hi = (addr + 0x8000) >> 16
        self.lui(rt, hi)
        self.addiu(rt, rt, addr - (hi << 16))

    def beq(self, rs, rt, t): self._branch(0x04, rs, rt, t)
    def bne(self, rs, rt, t): self._branch(0x05, rs, rt, t)
    def beqz(self, rs, t): self.beq(rs, "zero", t)
    def bnez(self, rs, t): self.bne(rs, "zero", t)
    def b(self, t): self.beq("zero", "zero", t)
    def blez(self, rs, t): self._branch(0x06, rs, "zero", t)
    def bgtz(self, rs, t): self._branch(0x07, rs, "zero", t)
    def bltz(self, rs, t): self._branch(0, rs, "zero", t, regimm=0)
    def bgez(self, rs, t): self._branch(0, rs, "zero", t, regimm=1)

    def j(self, t):
        self._emit(lambda pc, L: (2 << 26) | ((self._target(t, L) >> 2) & 0x3FFFFFF))

    def jal(self, t):
        self._emit(lambda pc, L: (3 << 26) | ((self._target(t, L) >> 2) & 0x3FFFFFF))

    def assemble(self):
        return [fn(self.origin + 4 * k, self.labels) for k, fn in enumerate(self.items)]
