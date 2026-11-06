"""item_text.py: the EXE's stat-sheet descriptions are fields, not prose (`ランク３　　長剣{n}火　片手主　ラン専用`), so generate them.

    python -X utf8 tools/item_text.py   writes script/exe.json `en` for every line whose fields are all in the tables, lists the rest

Lines with free text go through batches.py. Never overwrites English. The field words are in glossary.md (Stat sheet terms).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402

KIND = {
    "長剣": "Long Sword", "大剣": "Great Sword", "短剣": "Dagger", "ショートソード": "Short Sword", "細身剣": "Rapier", "刀": "Katana",
    "脇差": "Wakizashi", "杖": "Staff", "杭": "Stake", "棍棒": "Club", "鞭": "Whip", "扇": "Fan", "竪琴": "Lyre", "呪符": "Talisman",
    "妖斬糸": "Wire", "忍び武器": "Ninja Tool", "鉄拳": "Knuckles", "ポールウエポン": "Polearm", "重破砕武器": "Crusher", "盾": "Shield",
    "聖なる品": "Holy Item", "素手": "Bare Hands", "素鎧": "No Armor", "ハーフプレート": "Half Plate", "フルプレート": "Full Plate",
    "ブレストプレート": "Breastplate", "レザーアーマー": "Leather Armor", "マント": "Cloak", "ローブ": "Robe", "テスト": "Test",
    "テストデータ": "Test Data", "貴重": "Key Item",
}
ELEMENT = {"無": "Neutral", "火": "Fire", "水": "Water", "地": "Earth", "風": "Wind", "光": "Light", "闇": "Dark"}
SLOT = {"両手主": "Two-Hand", "片手主": "Main", "片手副": "Off", "片手兼": "Either", "鎧": "Armor", "非装備": "Unequipped", "盾": "Shield"}
CLASS = {"重戦": "Heavy", "剣士": "Fencer", "魔剣": "Mystic", "侍": "Samurai", "忍者": "Ninja", "格闘": "Brawler", "吸血": "Vampire",
         "魔使": "Mage", "全員": "All", "ＤＳ": "D.S."}
SHAPE = {
    "単体": "Solo", "一体": "Unison", "連続": "Chain", "合成一体": "Combo Unison", "合成連続": "Combo Chain",
    "無属性": "Neutral", "火属性": "Fire", "水属性": "Water", "地属性": "Earth", "風属性": "Wind", "光属性": "Light", "闇属性": "Dark",
    "敵エリア": "Enemy Area", "味方エリア": "Ally Area", "両エリア": "Both Areas", "術者本人": "Self",
    "１×１マス": "1x1", "1×1マス": "1x1", "３×３マス": "3x3", "３×３ランダム": "3x3 Random", "３×３乱数": "3x3 Random",
}
EFFECT = {
    "ダメージ": "Damage", "即死": "Instant Death", "弾き飛ばし": "Knockback", "ランダム効果": "Random Effect", "昏倒": "Stun", "毒": "Poison",
    "睡眠": "Sleep", "脱力": "Lethargy", "魅了": "Charm", "ノイズ": "Noise", "不和": "Discord", "停止": "Stop", "ＨＰドレイン": "HP Drain",
    "ＨＰ＆ＭＰドレイン": "HP & MP Drain", "加速": "Haste", "怪力": "Might", "浮遊": "Levitate", "攻撃": "Attack", "復活": "Revive",
    "パワー": "Power", "波動": "Wave", "ＨＰ回復": "HP Heal", "ＨＰ回復（小）": "HP Heal (S)", "ＨＰ回復（中）": "HP Heal (M)",
    "ＨＰ回復（大）": "HP Heal (L)", "ＨＰ全回復": "Full HP Heal", "ＭＰ回復": "MP Heal", "ＨＰ＆ＭＰ回復": "HP & MP Heal",
    "毒回復": "Cure Poison", "脱力回復": "Cure Lethargy", "魅了回復": "Cure Charm", "ノイズ回復": "Cure Noise", "不和回復": "Cure Discord",
    "毒＆脱力回復": "Cure Poison, Lethargy", "魅了＆ノイズ回復": "Cure Charm, Noise", "不和・昏倒・睡眠回復": "Cure Discord, Stun, Sleep",
    "全バッドステイタス回復": "Cure All Ailments", "防御力アップ": "Defense Up", "魔法抵抗力アップ": "Resist Up", "物理シールド": "Physical Shield",
    "魔法シールド": "Magic Shield", "魔法反射": "Magic Reflect", "メンタルシールド": "Mental Shield", "敵物理シールドダウン": "Enemy Shield Down",
    "防物理シールドダウン": "Shield Down", "障害物発生": "Make Obstacle", "敵消去": "Erase Enemy", "テレポート": "Teleport", "ターンアンデッド": "Turn Undead",
    "アンデッド破壊": "Destroy Undead", "ブラックホール出現": "Black Hole", "ブラックホール発生": "Black Hole", "マグネット出現": "Magnet",
    "ダメージトラップ": "Damage Trap", "停止トラップ": "Stop Trap", "ＭＰダメージトラップ": "MP Damage Trap", "ダメージ地帯発生": "Damage Zone",
    "停止地帯発生": "Stop Zone", "ノイズ地帯発生": "Noise Zone", "毒地帯発生": "Poison Zone", "睡眠地帯発生": "Sleep Zone", "脱力地帯発生": "Lethargy Zone",
    "魅了地帯発生": "Charm Zone", "アンデッド消去穴出現": "Undead Hole", "インセクト消去穴出現": "Insect Hole", "ビースト消去穴出現": "Beast Hole",
    "フィールド状態初期化": "Reset Field", "キャラクター状態初期化": "Reset Status", "ヨーコ玉ＭＰ回復": "Yoko Orb MP Heal", "？？？": "???",
    "ＭＰ全消費で復活＋ＨＰ全回復": "All MP: Revive, Full HP", "攻撃＋ＨＰ＆ＭＰドレイン＋脱力": "Attack, HP & MP Drain, Lethargy",
}
ASCII = str.maketrans("０１２３４５６７８９", "0123456789")


def people(field):
    """単体１人 -> Solo 1P"""
    m = re.fullmatch(r"(単体|一体|連続|合成一体|合成連続)([１-４])人", field)
    return f"{SHAPE[m.group(1)]} {m.group(2).translate(ASCII)}P" if m else None


def effect(field):
    if field in EFFECT:
        return EFFECT[field]
    parts = field.split("＋")
    if len(parts) > 1 and all(p in EFFECT for p in parts):
        return " + ".join(EFFECT[p] for p in parts)
    return None


def who(field):
    for suffix, fmt in (("専用", "{} only"), ("用", "for {}")):
        if field.endswith(suffix):
            name = field[:-len(suffix)]
            if name in NAMES:
                return fmt.format(NAMES[name])
            if name in CLASS:
                return fmt.format(CLASS[name])
    parts = field.split("／")
    return "/".join(CLASS[p] for p in parts) if all(p in CLASS for p in parts) else None


def rank_line(jp):
    """ランク３　　長剣{n}火　片手主　ラン専用; the class field can be empty."""
    m = re.fullmatch(r"ランク([０-９]+|？？)[　 ]*(.+?)\{n\}(.)　(.+?)(?:　(.+))?", jp.replace("鎧　非装備", "非装備"))
    if not m:
        return None
    rank, kind_, el, slot, cls = m.groups()
    rare = kind_.endswith("　貴重")
    kind_ = kind_.removesuffix("　貴重")
    if kind_ not in KIND or el not in ELEMENT or slot not in SLOT or (cls and not (who(cls) or cls == "テストデータ")):
        return None
    tail = [ELEMENT[el], SLOT[slot]] + ([who(cls) or "Test"] if cls else [])
    return f"Rank {rank.translate(ASCII).replace('？', '?')} {KIND[kind_]}{' (Rare)' if rare else ''} // " + " ".join(tail)


def skill_line(jp):
    """単体１人　無属性　３×３マス{n}毒"""
    if "{n}" not in jp:
        return None
    head, _, tail = jp.partition("{n}")
    out = []
    for field in head.split("　"):
        got = people(field) or SHAPE.get(field)
        if not got:
            return None
        out.append(got)
    e = effect(tail)
    return " ".join(out) + " // " + e if e else None


NAMES = {}


def main():
    global NAMES
    tbl = json.loads((ROOT / "script/tbl_0382.json").read_text(encoding="utf-8"))
    NAMES = {e["jp"]: e["en"] for e in tbl if e.get("en")}
    NAMES["ルーシェ"] = "Lucien"
    path = ROOT / "script/exe.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    terms = batches.glossary()
    done, left = 0, []
    for e in rows:
        if e["kind"] != "text" or e["off"] < 0x20000 or e.get("en"):
            continue
        a = rank_line(e["jp"]) or skill_line(e["jp"])
        if not a:
            left.append(e["jp"])
            continue
        try:
            en = batches.render(e, a)
        except ValueError:  # a body-armor rank line: the kind already says it's armor
            try:
                en = batches.render(e, a.replace(" Armor ", " ").replace(" Shield ", " "))
            except ValueError:
                left.append(e["jp"])
                continue
        bad = batches.problems(e, en, terms)
        if bad:
            print(e["id"], e["jp"], en, bad)
            continue
        e["en"] = en
        done += 1
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{done} generated, {len(left)} left for batches")
    print("~".join(left))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
