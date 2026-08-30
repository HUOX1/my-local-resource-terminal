from pathlib import Path
SCRIPTS=Path(__file__).parents[1]/"g3_frontend"/"scripts"
def test_variant_values_use_str_not_string_constructor():
    offenders=[]
    for path in sorted(SCRIPTS.glob("*.gd")):
        for number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),start=1):
            if "String(" in line: offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert offenders == [], "Variant string casts must use str(...):\n" + "\n".join(offenders)
