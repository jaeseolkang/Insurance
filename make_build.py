# 2026-10-16 07:15 KST | 수정: 구매자별 파일 생성 스크립트 최초 작성 (구매 이메일+임시번호 → 이용자 확인 정보를 넣은 HTML·zip·안내문 생성)
"""
구매자별 파일 만들기 (내 PC에서만 실행, 결과물은 깃에 올리지 않습니다)

사용법 (명령 프롬프트나 터미널에서, 이 파일이 있는 폴더에서):
    python make_build.py --email 구매자@example.com --order 20261016-001

옵션:
    --order     구매 번호(스마트스토어 주문번호 등). 생략하면 날짜시간으로 자동 생성
    --template  판매용 원본 HTML. 생략하면 같은 폴더의 index_local.html, 없으면 가장 최신 index_local_v*.html
    --out       결과를 저장할 폴더 (기본: builds)
    --code      임시번호를 직접 정할 때만 사용. 생략하면 8자리 무작위 번호 생성
    --no-zip    zip 파일을 만들지 않음
    --force     같은 이름의 결과 파일이 있어도 덮어씀
    --verify 파일.html --email 메일 --code 번호   만든 파일에서 이메일+임시번호가 맞는지 확인

결과물 (builds 폴더):
    {구매번호}_{이메일앞부분}.html   구매자 전용 앱 파일
    {구매번호}_{이메일앞부분}.zip    위 파일을 zip으로 묶은 것 (메일 첨부용)
    {구매번호}_{이메일앞부분}_안내.txt   메일 본문·임시번호 문자 문구
    ledger.csv                       발급 기록 (임시번호는 기록하지 않음)
"""
import argparse
import csv
import hashlib
import json
import re
import secrets
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ITER = 150000                                    # 앱(index_local_v3.html)의 확인 방식과 같아야 합니다
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"    # 헷갈리는 글자(0, O, 1, I) 제외
MARKER = "window.FP_LICENSE = null;"
LIC_RE = re.compile(r"^window\.FP_LICENSE = (\{.*\});[^\n]*$", re.M)


def norm_code(code: str) -> str:
    return re.sub(r"[\s-]", "", code).upper()


def derive(email: str, code: str, salt: str) -> str:
    """앱 안의 브라우저 계산과 같은 값: PBKDF2-SHA256, 비밀번호 = 이메일(소문자):임시번호(대문자, 하이픈 제거)"""
    pw = f"{email.strip().lower()}:{norm_code(code)}".encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", pw, salt.encode("utf-8"), ITER, dklen=32).hex()


def new_code() -> str:
    c = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"{c[:4]}-{c[4:]}"


def slug(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "_", text).strip("_")[:40] or "x"


def find_template(arg, here: Path) -> Path:
    if arg:
        p = Path(arg)
        if not p.is_file():
            sys.exit(f"원본 파일을 찾을 수 없습니다: {p}")
        return p
    p = here / "index_local.html"
    if p.is_file():
        return p
    cands = sorted(here.glob("index_local_v*.html"), key=lambda x: int(re.search(r"_v(\d+)", x.name).group(1)) if re.search(r"_v(\d+)", x.name) else 0)
    if cands:
        return cands[-1]
    sys.exit("원본 파일(index_local.html 또는 index_local_v*.html)이 이 폴더에 없습니다. --template으로 지정하세요.")


def ensure_gitignore(here: Path, out: Path) -> None:
    """결과 폴더가 깃에 올라가지 않도록 .gitignore에 추가"""
    try:
        rel = out.resolve().relative_to(here.resolve()).as_posix().rstrip("/") + "/"
    except ValueError:
        return                                      # 저장소 밖 폴더면 신경 쓸 필요 없음
    gi = here / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.is_file() else []
    if rel in lines or rel.rstrip("/") in lines:
        return
    with gi.open("a", encoding="utf-8") as f:
        f.write(("\n" if lines and lines[-1] else "") + rel + "\n")
    print(f"[알림] .gitignore에 '{rel}'를 추가했습니다 (구매자 파일이 깃에 올라가지 않도록).")


def verify(path: str, email: str, code: str) -> int:
    txt = Path(path).read_text(encoding="utf-8")
    m = LIC_RE.search(txt)
    if not m:
        print("이 파일에는 구매자 정보가 들어 있지 않습니다 (원본 파일이거나 형식이 다릅니다).")
        return 2
    lic = json.loads(m.group(1))
    ok = derive(email, code, lic["salt"]) == lic["hash"]
    print(f"구매 이메일: {lic['email']} / 구매번호: {lic.get('order', '')}")
    print("확인 결과:", "맞습니다 (앱에서도 통과합니다)" if ok else "맞지 않습니다")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="구매자별 파일 만들기")
    ap.add_argument("--email")
    ap.add_argument("--order")
    ap.add_argument("--template")
    ap.add_argument("--out", default="builds")
    ap.add_argument("--code")
    ap.add_argument("--no-zip", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--verify")
    a = ap.parse_args()

    if a.verify:
        if not (a.email and a.code):
            sys.exit("--verify에는 --email과 --code가 필요합니다.")
        sys.exit(verify(a.verify, a.email, a.code))

    if not a.email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", a.email.strip()):
        sys.exit("--email에 올바른 구매자 이메일을 넣어 주세요.")
    email = a.email.strip()
    order = (a.order or datetime.now().strftime("%Y%m%d-%H%M%S")).strip()
    here = Path(__file__).resolve().parent
    tpl = find_template(a.template, here)
    html = tpl.read_text(encoding="utf-8")
    if html.count(MARKER) != 1:
        sys.exit(f"원본 파일에서 '{MARKER}' 줄을 정확히 한 개 찾지 못했습니다. 이용자 확인 기능이 들어 있는 최신 원본(index_local_v3 이상)인지 확인하세요.")

    code = a.code or new_code()
    if len(norm_code(code)) < 6:
        sys.exit("임시번호는 6자 이상이어야 합니다.")
    salt = secrets.token_hex(16)
    lic = {"email": email, "order": order, "salt": salt, "iter": ITER, "hash": derive(email, code, salt)}
    line = "window.FP_LICENSE = " + json.dumps(lic, ensure_ascii=False, separators=(",", ":")) + ";   // 구매자별 파일"
    out_html = html.replace(MARKER, line)

    out = Path(a.out)
    if not out.is_absolute():
        out = here / out
    out.mkdir(parents=True, exist_ok=True)
    name = f"{slug(order)}_{slug(email.split('@')[0])}"
    f_html, f_zip, f_txt = out / f"{name}.html", out / f"{name}.zip", out / f"{name}_안내.txt"
    if not a.force:
        for f in (f_html, f_zip, f_txt):
            if f.exists():
                sys.exit(f"이미 있습니다: {f.name} (덮어쓰려면 --force, 재발급이면 구매번호를 바꿔 주세요)")
    f_html.write_text(out_html, encoding="utf-8")
    if not a.no_zip:
        with zipfile.ZipFile(f_zip, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(f_html, "FP고객관리.html")

    attach = f_zip.name if not a.no_zip else f_html.name
    f_txt.write_text(
        f"""[메일 본문 - 구매자에게 보내는 메일]
제목: [FP 고객관리] 구매해 주셔서 감사합니다 (구매번호 {order})

안녕하세요. 구매해 주셔서 감사합니다.
첨부 파일({attach})이 구매자님 전용 파일입니다.

1. 파일을 열면 '이용자 확인' 화면이 나옵니다. 구매하신 이메일({email})을 입력하세요.
2. 임시번호는 보안을 위해 문자(또는 톡톡)로 따로 보내드립니다. 받으신 임시번호를 입력하세요.
   (이 기기에서 처음 한 번만 입력합니다. 기기를 바꾸거나 브라우저 데이터를 지우면 다시 입력해야 하니 임시번호를 보관해 주세요.)
3. 이용약관을 읽고 동의하면 사용할 수 있습니다.
4. 고객 정보는 이 기기에만 저장됩니다. 설정의 '전체 백업 받기'로 정기적으로 백업하세요.
5. 이 파일과 임시번호는 구매자님 본인만 사용할 수 있으며, 다른 사람에게 전달·공유하면 이용약관에 따라 이용이 제한될 수 있습니다.

문의: drimsw@gmail.com


[문자/톡톡 - 임시번호만 따로 보냅니다]
[FP 고객관리] 구매번호 {order} 임시번호: {code}
(메일로 받은 파일을 처음 열 때 구매 이메일과 함께 입력하세요. 타인에게 알려 주지 마세요.)
""",
        encoding="utf-8",
    )

    ledger = out / "ledger.csv"
    new = not ledger.exists()
    with ledger.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["발급일시", "구매번호", "이메일", "파일", "원본", "확인값앞8자리"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order, email, f_html.name, tpl.name, lic["hash"][:8]])

    ensure_gitignore(here, out)
    print("만들었습니다.")
    print(f"  파일      : {f_html}")
    if not a.no_zip:
        print(f"  zip(첨부용): {f_zip}")
    print(f"  안내문    : {f_txt}")
    print(f"  임시번호  : {code}   ← 파일과 다른 경로(문자·톡톡)로 보내세요")
    print("  이 파일들은 깃에 올리지 마세요.")


if __name__ == "__main__":
    main()
