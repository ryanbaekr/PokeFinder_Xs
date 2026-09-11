from typing import Mapping
from typing import MutableSequence
from typing import Optional
from typing import Tuple


class Xorshift:
    def __init__(self, seed0: int, seed1: int, seed2: int, seed3: int):
        self.seed0: int = seed0
        self.seed1: int = seed1
        self.seed2: int = seed2
        self.seed3: int = seed3

    def next(self) -> int:
        temp = self.seed0 ^ self.seed0 << 11 & 0xFFFFFFFF
        self.seed0 = self.seed1
        self.seed1 = self.seed2
        self.seed2 = self.seed3
        self.seed3 = temp ^ temp >> 8 ^ self.seed3 ^ self.seed3 >> 19

        return self.seed3

    def prev(self) -> int:
        temp = self.seed2 >> 19 ^ self.seed2 ^ self.seed3
        temp ^= temp >> 8
        temp ^= temp >> 16

        temp ^= temp << 11 & 0xFFFFFFFF
        temp ^= temp << 22 & 0xFFFFFFFF

        self.seed3 = self.seed2
        self.seed2 = self.seed1
        self.seed1 = self.seed0
        self.seed0 = temp

        return self.seed3

    def get_next_rand_sequence(self, length: int) -> MutableSequence[int]:
        return [self.next() for _ in range(length)]

    def get_state(self) -> MutableSequence[int]:
        return [self.seed0, self.seed1, self.seed2, self.seed3]


class XoroshiroBDSP:
    def __init__(self, seed: int):
        self.seed: MutableSequence[int] = [
            self._splitmix(seed, 0x9E3779B97F4A7C15),
            self._splitmix(seed, 0x3C6EF372FE94F82A),
        ]

    @staticmethod
    def _splitmix(seed: int, state: int) -> int:
        seed += state
        seed2: int = (0xBF58476D1CE4E5B9 * (seed ^ (seed >> 30))) & 0xFFFFFFFFFFFFFFFF
        seed3: int = (0x94D049BB133111EB * (seed2 ^ (seed2 >> 27))) & 0xFFFFFFFFFFFFFFFF
        return seed3 ^ (seed3 >> 31)

    @staticmethod
    def _rotl(x: int, k: int) -> int:
        return ((x << k) | (x >> (64 - k))) & 0xFFFFFFFFFFFFFFFF

    def next(self, max: Optional[int] = None) -> int:
        s0: int = self.seed[0]
        s1: int = self.seed[1]
        result: int = (s0 + s1) & 0xFFFFFFFFFFFFFFFF

        s1 ^= s0
        self.seed[0] = self._rotl(s0, 24) ^ s1 ^ ((s1 << 16) & 0xFFFFFFFFFFFFFFFF)
        self.seed[1] = self._rotl(s1, 37)

        if max:
            return (result >> 32) % max
        else:
            return result >> 32


def is_shiny(pid: int, tsv: int) -> int:
    psv: int = (pid >> 16) ^ (pid & 0xFFFF)
    return (tsv ^ psv) < 16


def generate(
    tid: int,
    sid: int,
    shiny_charm: bool,
    oval_charm: bool,
    compatibility_str: str,
    gender_ratio_str: str,
    masuda: bool,
    seed0: int,
    seed1: int,
    initial_advances: int,
    max_advances: int,
) -> MutableSequence[Mapping[str, str]]:
    compatibility_map: Mapping[Tuple[str, bool], int] = {
        ("The two don't seem to like each other", False): 20,
        ("The two seem to get along", False): 50,
        ("The two seem to get along very well", False): 70,
        ("The two don't seem to like each other", True): 40,
        ("The two seem to get along", True): 80,
        ("The two seem to get along very well", True): 88,
    }

    gender_ratio_map: Mapping[str, int] = {
        "Genderless": 255,
        "100% F": 254,
        "25% M / 75% F": 191,
        "50% M / 50% F": 127,
        "75% M / 25% F": 63,
        "88% M / 12% F": 31,
        "Nidoran / VI": 1,
        "100% M": 0,
    }

    gender_map: Mapping[int, str] = {
        0: "M",
        1: "F",
        2: "-",
    }

    nature_map: Mapping[int, str] = {
        0: "Hardy",
        1: "Lonely",
        2: "Brave",
        3: "Adamant",
        4: "Naughty",
        5: "Bold",
        6: "Docile",
        7: "Relaxed",
        8: "Impish",
        9: "Lax",
        10: "Timid",
        11: "Hasty",
        12: "Serious",
        13: "Jolly",
        14: "Naive",
        15: "Modest",
        16: "Mild",
        17: "Quiet",
        18: "Bashful",
        19: "Rash",
        20: "Calm",
        21: "Gentle",
        22: "Sassy",
        23: "Careful",
        24: "Quirky",
    }

    # one time calc
    tsv: int = tid ^ sid
    compatibility: int = compatibility_map[(compatibility_str, oval_charm)]
    gender_ratio: int = gender_ratio_map[gender_ratio_str]

    rng_list: Xorshift = Xorshift(seed0 >> 32, seed0 & 0xFFFFFFFF, seed1 >> 32, seed1 & 0xFFFFFFFF)

    pid_rolls: int = 0
    if masuda:
        pid_rolls += 6
    if shiny_charm:
        pid_rolls += 2

    inheritance_count: int = 3
    # TODO handle items - inheritance_count can increase to 5

    hits: MutableSequence[Mapping[str, str]] = []

    for count in range(0, max_advances + 1):
        if (((rng_list.next() % 0xFFFFFFFF) + 0x80000000) & 0xFFFFFFFF) % 100 < compatibility:
            sem: int = 0x80000000
            seed: int = ((((rng_list.next() % 0xFFFFFFFF) + 0x80000000) & 0xFFFFFFFF) ^ sem) - sem

            rng: XoroshiroBDSP = XoroshiroBDSP(seed)

            if gender_ratio == 255:
                gender: int = 2
            elif gender_ratio == 254:
                gender: int = 1
            elif gender_ratio == 1:
                gender: int = rng.next(2)
            elif gender_ratio == 0:
                gender: int = 0
            else:
                gender: int = int((rng.next(252) + 1) < gender_ratio)

            nature: int = rng.next(25)
            # TODO handle items - match parent nature

            ability: int = rng.next(100)
            # TODO determine ability from percent

            inheritance_array: MutableSequence[int] = [0, 0, 0, 0, 0, 0]
            i: int = 0
            while i < inheritance_count:
                index: int = rng.next(6)
                if inheritance_array[index] == 0:
                    inheritance_array[index] = rng.next(2) + 1
                    i += 1

            iv_array: MutableSequence[int] = []
            for i in range(6):
                iv: int = rng.next(32)
                if inheritance_array[i] == 1:
                    iv_array.append(-1)
                elif inheritance_array[i] == 2:
                    iv_array.append(-2)
                else:
                    iv_array.append(iv)

            ec: int = rng.next(0xFFFFFFFF)

            for _ in range(pid_rolls):
                pid: int = rng.next(0xFFFFFFFF)
                if is_shiny(pid, tsv):
                    if count >= initial_advances:
                        hits.append(
                            {
                                "Advances": f"{count}",
                                "Egg Seed": f"{seed & 0xFFFFFFFF:X}",
                                "PID": f"{pid & 0xFFFFFFFF:X}",
                                "Shiny": "Yes",
                                "Nature": f"{nature_map[nature]}",
                                "Ability": f"{ability}",
                                "HP": f"{iv_array[0]}",
                                "Atk": f"{iv_array[1]}",
                                "Def": f"{iv_array[2]}",
                                "SpA": f"{iv_array[3]}",
                                "SpD": f"{iv_array[4]}",
                                "Spe": f"{iv_array[5]}",
                                "Gender": f"{gender_map[gender]}",
                                "EC": f"{ec & 0xFFFFFFFF:X}",
                            }
                        )
                    break

            rng_list.prev()

    return hits


if __name__ == "__main__":
    # game data
    tid: int = 12345
    sid: int = 54321
    shiny_charm: bool = True
    oval_charm: bool = True

    # daycare data
    compatibility_str: str = "The two seem to get along"
    gender_ratio_str: str = "Nidoran / VI"
    masuda: bool = True

    # rng data
    seed0: int = 0x1234567887654321
    seed1: int = 0x8765432112345678
    initial_advances: int = 0
    max_advances: int = 10000

    print(generate(
        tid,
        sid,
        shiny_charm,
        oval_charm,
        compatibility_str,
        gender_ratio_str,
        masuda,
        seed0,
        seed1,
        initial_advances,
        max_advances,
    ))

""" TODO
- Account for items
- Calculate actual Ability
"""
