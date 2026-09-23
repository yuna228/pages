import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st


# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="학교 급식 찾아보기",
    page_icon="🍱",
    layout="centered",
)

SCHOOL_API_URL = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

MIN_DATE = date(2026, 3, 4)
MAX_DATE = date(2026, 10, 30)

KST = ZoneInfo("Asia/Seoul")
TODAY_KST = datetime.now(KST).date()


# =========================
# 함수
# =========================

def get_school_list(school_name):
    """학교 이름으로 학교 목록을 조회한다."""

    params = {
        "Type": "json",
        "SCHUL_NM": school_name,
    }

    try:
        response = requests.get(
            SCHOOL_API_URL,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException:
        return None, "학교 정보를 가져오는 중 네트워크 오류가 발생했습니다."

    except ValueError:
        return None, "학교 정보 API의 응답을 읽을 수 없습니다."

    # 정상적인 schoolInfo 구조 확인
    if "schoolInfo" not in data:
        return None, "학교 정보 API에서 예상하지 못한 응답이 왔습니다."

    school_info = data["schoolInfo"]

    # RESULT가 들어온 경우
    for box in school_info:
        if "head" in box:
            for item in box["head"]:
                result = item.get("RESULT")
                if result:
                    code = result.get("CODE")
                    message = result.get("MESSAGE", "")

                    if code == "INFO-200":
                        return [], None

                    return None, f"학교 정보 조회 오류: {message}"

    # 두 번째 상자의 row 찾기
    rows = []

    for box in school_info:
        if "row" in box:
            rows = box["row"]
            break

    return rows, None


def get_meal_info(school, selected_date):
    """선택한 학교의 선택 날짜 중식 정보를 조회한다."""

    date_string = selected_date.strftime("%Y%m%d")

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": school["ATPT_OFCDC_SC_CODE"],
        "SD_SCHUL_CODE": school["SD_SCHUL_CODE"],
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": date_string,
        "MLSV_TO_YMD": date_string,
        "pSize": "1000",
        "pIndex": "1",
    }

    try:
        response = requests.get(
            MEAL_API_URL,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException:
        return None, "급식 정보를 가져오는 중 네트워크 오류가 발생했습니다."

    except ValueError:
        return None, "급식 정보 API의 응답을 읽을 수 없습니다."

    if "mealServiceDietInfo" not in data:
        return None, "급식 정보 API에서 예상하지 못한 응답이 왔습니다."

    meal_info = data["mealServiceDietInfo"]

    # RESULT 확인
    for box in meal_info:
        if "head" in box:
            for item in box["head"]:
                result = item.get("RESULT")

                if result:
                    code = result.get("CODE")
                    message = result.get("MESSAGE", "")

                    # 조회 결과 없음은 정상적인 상황
                    if code == "INFO-200":
                        return [], None

                    return None, f"급식 정보 조회 오류: {message}"

    # row 찾기
    rows = []

    for box in meal_info:
        if "row" in box:
            rows = box["row"]
            break

    return rows, None


def clean_menu_text(menu):
    """
    DDISH_NM의 <br/> 등을 줄바꿈으로 바꾼다.
    알레르기 번호가 들어 있는 괄호 내용은 그대로 유지한다.
    """
    if not menu:
        return ""

    # 줄바꿈 태그를 실제 줄바꿈으로 변환
    text = re.sub(r"<br\s*/?>", "\n", menu, flags=re.IGNORECASE)

    # 혹시 다른 HTML 태그가 있다면 제거
    text = re.sub(r"<[^>]+>", "", text)

    return text.strip()


# =========================
# 화면
# =========================

st.title("🍱 학교 급식 찾아보기")

st.write(
    "학교 이름을 검색한 뒤 학교를 선택하고, "
    "날짜를 고르면 그날의 중식 메뉴를 확인할 수 있습니다."
)


# -------------------------
# 학교 검색
# -------------------------

st.subheader("1. 학교 선택")

school_name = st.text_input(
    "학교 이름",
    placeholder="예: 평택고, 서울고, ○○초등학교",
)

search_button = st.button(
    "학교 찾기",
    type="primary",
)


if search_button:
    if not school_name.strip():
        st.warning("학교 이름을 입력해 주세요.")
        st.session_state["school_results"] = None
    else:
        with st.spinner("학교를 찾는 중입니다..."):
            schools, error = get_school_list(school_name.strip())

        if error:
            st.error(error)
            st.session_state["school_results"] = None

        elif not schools:
            st.session_state["school_results"] = []
            st.info(
                f"'{school_name.strip()}'이(가) 들어간 학교를 찾지 못했습니다. "
                "학교 이름을 조금 다르게 입력해 보세요."
            )

        else:
            st.session_state["school_results"] = schools


schools = st.session_state.get("school_results")


# -------------------------
# 학교 선택
# -------------------------

if schools:
    school_options = []

    for school in schools:
        school_options.append(
            (
                f"{school.get('SCHUL_NM', '')} "
                f"— {school.get('LCTN_SC_NM', '')}",
                school,
            )
        )

    selected_label = st.selectbox(
        "검색된 학교 중 하나를 선택하세요.",
        options=[item[0] for item in school_options],
    )

    selected_school = next(
        item[1]
        for item in school_options
        if item[0] == selected_label
    )

    st.caption(
        f"선택한 학교: {selected_school.get('SCHUL_NM', '')} "
        f"({selected_school.get('LCTN_SC_NM', '')})"
    )

    st.divider()

    # -------------------------
    # 날짜 선택
    # -------------------------

    st.subheader("2. 날짜 선택")

    # 오늘이 허용 범위 밖인 경우에도 date_input이 정상적으로 작동하도록
    # 범위 안의 날짜를 기본값으로 사용한다.
    default_date = TODAY_KST

    if default_date < MIN_DATE:
        default_date = MIN_DATE
    elif default_date > MAX_DATE:
        default_date = MAX_DATE

    selected_date = st.date_input(
        "급식 날짜",
        value=default_date,
        min_value=MIN_DATE,
        max_value=MAX_DATE,
        format="YYYY-MM-DD",
    )

    st.caption(
        f"조회 가능 기간: {MIN_DATE.strftime('%Y-%m-%d')} ~ "
        f"{MAX_DATE.strftime('%Y-%m-%d')}"
    )

    # -------------------------
    # 급식 조회
    # -------------------------

    st.divider()

    st.subheader("3. 중식")

    with st.spinner("급식 정보를 불러오는 중입니다..."):
        meals, error = get_meal_info(
            selected_school,
            selected_date,
        )

    if error:
        st.error(error)

    elif not meals:
        st.info(
            f"{selected_date.strftime('%Y년 %m월 %d일')}에는 "
            "등록된 중식 정보가 없습니다."
        )

    else:
        # 일반적으로 하루에 중식 1건이지만,
        # 여러 행이 반환될 경우 모두 표시
        for meal in meals:
            meal_date = meal.get("MLSV_YMD", "")
            menu = clean_menu_text(meal.get("DDISH_NM", ""))
            calories = meal.get("CAL_INFO", "")

            if meal_date:
                try:
                    formatted_date = datetime.strptime(
                        meal_date,
                        "%Y%m%d",
                    ).strftime("%Y년 %m월 %d일")
                except ValueError:
                    formatted_date = meal_date
            else:
                formatted_date = selected_date.strftime("%Y년 %m월 %d일")

            st.markdown(f"### 🍚 {formatted_date}")

            if menu:
                # 메뉴 원문에 포함된 알레르기 번호를 그대로 보여준다.
                st.text(menu)
            else:
                st.info("등록된 메뉴 정보가 없습니다.")

            if calories:
                st.markdown(f"**칼로리:** {calories}")

else:
    if not search_button and "school_results" not in st.session_state:
        st.info("학교 이름을 입력하고 **학교 찾기**를 눌러 주세요.")
