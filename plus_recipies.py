import os
import json
import re
import xml.etree.ElementTree as ET
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# .env 로드 (python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def save_recipes_to_json(limit: int | None = None):
    """
    농림수산식품교육문화정보원 레시피 API 3종에서 칼럼 수집 후 JSON 저장.
    EPIS_API_KEY(.env) 필수. 공공데이터포털(data.go.kr)에서 발급.

    Args:
        limit: 조회할 row 개수. None이면 전체 데이터 수집 (페이지네이션)
    """
    base_url = "http://211.237.50.150:7080/openapi"
    api_key = os.getenv("EPIS_API_KEY", "").strip()

    if not api_key:
        print("오류: EPIS_API_KEY가 .env에 설정되지 않았습니다.")
        print("  공공데이터포털(data.go.kr) → 농림수산식품교육문화정보원 레시피 API 활용신청 후 인증키 발급")
        return None

    SERVICES = {
        "info": "Grid_20150827000000000226_1",
        "irdnt": "Grid_20150827000000000227_1",
        "crse": "Grid_20150827000000000228_1",
    }

    def fetch_api(service_id: str, start: int = 1, end: int = 100, use_xml: bool = True):
        """인증키로 API 호출. use_xml=True면 XML로 요청."""
        fmt = "xml" if use_xml else "json"
        url = f"{base_url}/{api_key}/{fmt}/{service_id}/{start}/{end}"
        response = requests.get(url, timeout=30)

        if use_xml:
            root = ET.fromstring(response.content)
            if root.tag != service_id:
                result = root.find("result")
                if result is not None:
                    code = result.findtext("code", "")
                    msg = result.findtext("message", "")
                    raise RuntimeError(f"API 오류 ({service_id}): [{code}] {msg}")
                raise RuntimeError(f"API 응답 형식 오류: {service_id}")
            rows = []
            for row_el in root.findall("row"):
                row = {}
                for child in row_el:
                    tag = child.tag
                    val = child.text if child.text else ""
                    if "}" in child.tag:
                        tag = child.tag.split("}")[-1]
                    row[tag] = val.strip() if val else ""
                rows.append(row)
            return rows

        data = response.json()
        if service_id in data and "row" in data[service_id]:
            return data[service_id]["row"]
        if "result" in data:
            code = data["result"].get("code", "")
            msg = data["result"].get("message", "")
            raise RuntimeError(f"API 오류 ({service_id}): [{code}] {msg}")
        raise RuntimeError(f"API 응답 형식 오류: {service_id}")

    def fetch_all(service_id: str, max_per_request: int = 1000):
        """전체 데이터 페이지네이션으로 수집."""
        all_rows = []
        start = 1
        while True:
            end = start + max_per_request - 1
            rows = fetch_api(service_id, start, end)
            if not rows:
                break
            all_rows.extend(rows)
            print(f"  {service_id}: {len(all_rows)}건 수집 중...")
            if len(rows) < max_per_request:
                break
            start = end + 1
        return all_rows

    try:
        print("데이터 수집 중...")
        info_rows = fetch_all(SERVICES["info"]) if limit is None else fetch_api(SERVICES["info"], 1, min(limit, 1000))
        irdnt_rows = fetch_all(SERVICES["irdnt"]) if limit is None else fetch_api(SERVICES["irdnt"], 1, min(limit * 20, 1000))
        crse_rows = fetch_all(SERVICES["crse"]) if limit is None else fetch_api(SERVICES["crse"], 1, min(limit * 20, 1000))

        # 필요한 칼럼만 추출
        KEEP_COLUMNS = {
            "info": ["RECIPE_ID", "RECIPE_NM_KO", "COOKING_TIME", "QNT", "IMG_URL"],
            "irdnt": ["RECIPE_ID", "IRDNT_NM"],
            "crse": ["RECIPE_ID", "COOKING_NO", "COOKING_DC"],
        }

        def to_list(rows):
            if isinstance(rows, dict):
                return [rows]
            return list(rows) if rows else []

        def pick_columns(rows, columns):
            result = []
            for row in rows:
                filtered = {k: row.get(k) for k in columns}
                result.append(filtered)
            return result

        info_rows = pick_columns(to_list(info_rows), KEEP_COLUMNS["info"])
        irdnt_rows = pick_columns(to_list(irdnt_rows), KEEP_COLUMNS["irdnt"])
        crse_rows = pick_columns(to_list(crse_rows), KEEP_COLUMNS["crse"])

        # RECIPE_ID 기준 매핑 + 모델 칼럼명 변환
        def parse_minutes(s):
            if not s:
                return None
            m = re.search(r"\d+", str(s))
            return int(m.group()) if m else None

        def parse_servings(s):
            if not s:
                return None
            m = re.search(r"\d+", str(s))
            return int(m.group()) if m else None

        irdnt_by_id = {}
        for r in irdnt_rows:
            rid = r["RECIPE_ID"]
            if rid not in irdnt_by_id:
                irdnt_by_id[rid] = []
            irdnt_by_id[rid].append({"name_ko": r["IRDNT_NM"]})

        crse_by_id = {}
        for r in crse_rows:
            rid = r["RECIPE_ID"]
            if rid not in crse_by_id:
                crse_by_id[rid] = []
            crse_by_id[rid].append({
                "step": int(r["COOKING_NO"]) if r.get("COOKING_NO") else 0,
                "description": r.get("COOKING_DC", ""),
            })

        merged = []
        for info in info_rows:
            rid = info["RECIPE_ID"]
            steps = sorted(crse_by_id.get(rid, []), key=lambda x: x["step"])
            merged.append({
                "recipe_id": rid,
                "title": info.get("RECIPE_NM_KO", ""),
                "ready_minutes": parse_minutes(info.get("COOKING_TIME")),
                "servings": parse_servings(info.get("QNT")),
                "image_url": info.get("IMG_URL") or None,
                "instructions": steps,
                "ingredients": irdnt_by_id.get(rid, []),
            })

        output = {"recipes": merged}

        file_path = BASE_DIR / "recipes_data.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=4)

        print(f"성공! {file_path}에 저장되었습니다.")
        print(f"  RECIPE_ID 기준 매핑: {len(merged)}개 레시피")
        return str(file_path)

    except Exception as e:
        print(f"오류 발생: {e}")
        return None


def _parse_minutes(s):
    if not s:
        return None
    m = re.search(r"\d+", str(s))
    return int(m.group()) if m else None


def _parse_servings(s):
    if not s:
        return None
    m = re.search(r"\d+", str(s))
    return int(m.group()) if m else None


def merge_recipes_by_id(file_path: Path | None = None):
    """
    recipes_data.json을 RECIPE_ID 기준 병합 + 모델 칼럼명 변환.
    - raw(info, irdnt, crse) 또는 구 merged(RECIPE_ID, steps) → 새 형식(recipe_id, instructions, ingredients)
    """
    path = file_path or BASE_DIR / "recipes_data.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    def to_model_format(recipes):
        """병합된 레시피를 모델 칼럼명으로 변환"""
        result = []
        for r in recipes:
            rid = r.get("RECIPE_ID") or r.get("recipe_id")
            ingredients = r.get("ingredients", [])
            if ingredients and isinstance(ingredients[0], str):
                ingredients = [{"name_ko": x} for x in ingredients]
            steps = r.get("steps", r.get("instructions", []))
            if steps and isinstance(steps[0], dict) and "COOKING_NO" in steps[0]:
                steps = [{"step": int(s.get("COOKING_NO", i + 1)), "description": s.get("COOKING_DC", "")} for i, s in enumerate(steps)]
            result.append({
                "recipe_id": rid,
                "title": r.get("RECIPE_NM_KO", r.get("title", "")),
                "ready_minutes": _parse_minutes(r.get("COOKING_TIME")),
                "servings": _parse_servings(r.get("QNT")),
                "image_url": r.get("IMG_URL", r.get("image_url")) or None,
                "instructions": sorted(steps, key=lambda x: x.get("step", 0)) if steps else [],
                "ingredients": ingredients,
            })
        return result

    if "recipes" in data:
        r0 = data["recipes"][0] if data["recipes"] else {}
        if "recipe_id" in r0 and "instructions" in r0 and r0.get("ingredients") and isinstance(r0["ingredients"][0], dict):
            print("이미 모델 칼럼명 형식입니다.")
            return str(path)
        merged = to_model_format(data["recipes"])

    elif "info" in data:
        info = data["info"]
        irdnt = data["irdnt"]
        crse = data["crse"]

        irdnt_by_id = {}
        for r in irdnt:
            rid = r.get("RECIPE_ID")
            if rid not in irdnt_by_id:
                irdnt_by_id[rid] = []
            irdnt_by_id[rid].append({"name_ko": r.get("IRDNT_NM", "")})

        crse_by_id = {}
        for r in crse:
            rid = r.get("RECIPE_ID")
            if rid not in crse_by_id:
                crse_by_id[rid] = []
            no = r.get("COOKING_NO", "1")
            crse_by_id[rid].append({
                "step": int(no) if str(no).isdigit() else 0,
                "description": r.get("COOKING_DC", ""),
            })

        merged = []
        for info_row in info:
            rid = info_row.get("RECIPE_ID")
            merged.append({
                "recipe_id": rid,
                "title": info_row.get("RECIPE_NM_KO", ""),
                "ready_minutes": _parse_minutes(info_row.get("COOKING_TIME")),
                "servings": _parse_servings(info_row.get("QNT")),
                "image_url": info_row.get("IMG_URL") or None,
                "instructions": sorted(crse_by_id.get(rid, []), key=lambda x: x["step"]),
                "ingredients": irdnt_by_id.get(rid, []),
            })
    else:
        print("인식할 수 없는 형식입니다.")
        return None

    out = {"recipes": merged}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=4)
    print(f"병합 완료: {path} ({len(merged)}개 레시피)")
    return str(path)


def renumber_recipe_ids(start_id: int = 3000, file_path: Path | None = None):
    """recipe_id를 start_id부터 1씩 증가하도록 변경."""
    path = file_path or BASE_DIR / "recipes_data.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if "recipes" not in data:
        print("recipes 키가 없습니다.")
        return None

    for i, r in enumerate(data["recipes"]):
        r["recipe_id"] = str(start_id + i)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"recipe_id 변경 완료: {start_id} ~ {start_id + len(data['recipes']) - 1} ({len(data['recipes'])}개)")
    return str(path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--merge-only":
        merge_recipes_by_id()
    elif len(sys.argv) > 1 and sys.argv[1] == "--renumber":
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
        renumber_recipe_ids(start_id=start)
    else:
        save_recipes_to_json(limit=None)  # 전체 데이터
