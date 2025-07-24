import streamlit as st
import requests
import folium
import json # 이 모듈은 현재 코드에서 사용되지 않으므로 제거하거나 필요에 따라 활용하세요.

# 카카오 개발자 사이트에서 발급받은 JavaScript 키 (REST API 키 아님!)
# REST API 키를 사용해야 서버에서 직접 API 호출이 가능합니다.
# JavaScript 키는 주로 웹 프론트엔드에서 사용됩니다.
# Python 백엔드에서 호출하려면 REST API 키를 사용하세요.
# https://developers.kakao.com/docs/latest/ko/daum-search/dev-guide#api-keys
# 실제 발급받은 REST API 키로 변경. 이 키는 GitHub에 올릴 때 주의해야 합니다.
# 환경 변수로 관리하는 것이 좋습니다.
KAKAO_REST_API_KEY = st.secrets["KAKAO_REST_API_KEY"]

MY_ADDRESS = "충남 홍성군 청사로 15"

def get_coordinates_kakao(address):
    """카카오 로컬 API를 사용하여 주소를 위도, 경도 좌표로 변환합니다."""
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": address}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # HTTP 에러 발생 시 예외 발생
        data = response.json()
        if data and data['documents']:
            doc = data['documents'][0]
            return float(doc['y']), float(doc['x']) # 카카오는 위도, 경도 순서
        else:
            st.error(f"'{address}' 주소를 찾을 수 없습니다.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"카카오 지오코딩 API 호출 중 오류 발생: {e}")
        return None

def get_route_kakao(start_coords, end_coords):
    """카카오 길찾기 API를 사용하여 두 지점 간의 승용차 경로를 가져옵니다."""
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    # 시작점과 도착점 좌표 (경도, 위도 순서)
    params = {
        "origin": f"{start_coords[1]},{start_coords[0]}",
        "destination": f"{end_coords[1]},{end_coords[0]}",
        "priority": "RECOMMEND", # 추천 경로
        "road_types": "ROUTINE", # 일반 도로 우선
        "car_type": "1" # 승용차
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data and data['routes']:
            route_info = data['routes'][0]
            route_points = []
            total_distance = 0
            for section in route_info['sections']:
                for guide in section['guides']:
                    route_points.append((guide['y'], guide['x']))
                for road in section['roads']:
                    total_distance += road['distance'] 

            if route_points:
                # 간단화된 중간 지점 (경로의 중간 인덱스)
                # 실제 도로 위 중간 지점을 정확히 찾으려면 더 복잡한 계산이 필요합니다.
                # 여기서는 안내 지점 중 중간을 선택합니다.
                midpoint_index = len(route_points) // 2
                return route_points, route_points[midpoint_index], total_distance
            return [], None, 0
        else:
            st.warning("경로 정보를 찾을 수 없습니다.")
            return [], None, 0
    except requests.exceptions.RequestException as e:
        st.error(f"카카오 길찾기 API 호출 중 오류 발생: {e}")
        return [], None, 0

st.title("카카오api를 활용한 중간지점 찾기")
st.write("충남 내포신도시에 거주하는 민대식과 중간지점을 찾아주는 재미용 프로그램인것")

other_address = st.text_input("다른 사람의 주소를 입력하세요:", "서울시 강남구 테헤란로 427")

if st.button("중간 지점 찾기"):
    if not other_address:
        st.warning("주소를 입력해주세요.")
    else:
        my_coords = get_coordinates_kakao(MY_ADDRESS)
        other_coords = get_coordinates_kakao(other_address)

        if my_coords and other_coords:
            st.info(f"'{MY_ADDRESS}' ({my_coords[0]:.4f}, {my_coords[1]:.4f})와 "
                    f"'{other_address}' ({other_coords[0]:.4f}, {other_coords[1]:.4f}) 사이의 경로를 탐색합니다.")

            route_points, midpoint, total_distance = get_route_kakao(my_coords, other_coords)

            if route_points and midpoint:
                st.success(f"총 이동 거리: {total_distance / 1000:.2f} km")
                st.success(f"가장 중간 지점: 위도 {midpoint[0]:.4f}, 경도 {midpoint[1]:.4f}")

                # 지도 생성 및 표시
                center_lat = (my_coords[0] + other_coords[0]) / 2
                center_lng = (my_coords[1] + other_coords[1]) / 2
                m = folium.Map(location=[center_lat, center_lng], zoom_start=9)

                folium.Marker(my_coords, popup=f"출발지: {MY_ADDRESS}", icon=folium.Icon(color='blue', icon='home')).add_to(m)
                folium.Marker(other_coords, popup=f"도착지: {other_address}", icon=folium.Icon(color='red', icon='flag')).add_to(m)
                folium.Marker(midpoint, popup=f"가장 중간 지점\n위도: {midpoint[0]:.4f}\n경도: {midpoint[1]:.4f}", icon=folium.Icon(color='green', icon='info-sign')).add_to(m)

                folium.PolyLine(route_points, color="purple", weight=5, opacity=0.7).add_to(m)

                # Streamlit에서 Folium 지도를 표시하는 방법
                st_data = folium.Figure()
                m.add_to(st_data)
                st.components.v1.html(st_data.render(), height=500)
            else:
                st.warning("경로를 찾거나 중간 지점을 계산하는 데 문제가 발생했습니다. API 키나 주소 형식을 확인해주세요.")