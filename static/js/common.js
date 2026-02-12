// 공통 JS (네브바 동작 등)
/**
 * ★ [만능 함수] 토큰이 만료되면 알아서 재발급받고 재요청하는 fetch 래퍼 함수
 * 사용법: fetch(...) 대신 authFetch(...) 라고 쓰면 됨!
 */
async function authFetch(url, options = {}) {
    // 1. 기본 헤더 설정 (토큰 자동 포함)
    const token = localStorage.getItem('access_token');
    
    // options.headers가 없으면 빈 객체로 초기화
    if (!options.headers) {
        options.headers = {};
    }

    // 토큰이 있고, 헤더에 Authorization이 명시적으로 없을 때만 추가
    if (token && !options.headers['Authorization']) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    // 2. 원래 요청 시도
    let response = await fetch(url, options);

    // 3. 만약 401(토큰 만료) 에러가 났다? -> 심폐소생술(Refresh) 시도!
    if (response.status === 401) {
        console.log("토큰 만료 감지! 재발급 시도 중...");
        
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
            // 리프레시 토큰도 없으면 진짜 로그아웃
            forceLogout();
            return response;
        }

        // 토큰 재발급 요청 (방금 만든 URL)
        const refreshRes = await fetch('/users/token/refresh/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken }) // 라이브러리 기본 키값은 'refresh'
        });

        if (refreshRes.ok) {
            // 4. 재발급 성공! -> 새 토큰 저장
            const data = await refreshRes.json();
            localStorage.setItem('access_token', data.access);
            // (참고: refresh token은 보통 그대로 유지되거나 새로 올 수도 있음)
            
            console.log("토큰 갱신 성공! 원래 요청 재시도.");

            // 5. 새 토큰으로 헤더 갈아끼우기
            options.headers['Authorization'] = `Bearer ${data.access}`;
            
            // 6. 원래 하려던 요청 재시도 (재귀 호출 아님, 그냥 fetch 다시)
            response = await fetch(url, options);
        } else {
            // 7. 재발급도 실패함 (리프레시 토큰도 만료됨) -> 진짜 로그아웃
            console.log("리프레시 토큰도 만료됨.");
            forceLogout();
        }
    }

    return response;
}

// 강제 로그아웃 함수
function forceLogout() {
    alert("로그인 정보가 만료되었습니다. 다시 로그인해주세요.");
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_nickname');
    window.location.href = '/users/login/';
}