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
// ==========================================
// [스마트 알림 배지] 아까보다 위험 식재료가 늘어났을 때만 다시 알림!
// ==========================================
async function checkUnreadNotifications() {
    try {
        const response = await authFetch('/ingredients/api/user-ingredients/expiring_soon/');
        if (!response.ok) return;
        
        const data = await response.json();
        const badges = document.querySelectorAll('.noti-badge');
        
        if (badges.length > 0) {
            const lastSeenDate = localStorage.getItem('last_seen_noti_date');
            // [추가] 이전에 확인했던 알림 개수 불러오기 (없으면 0)
            const lastSeenCount = parseInt(localStorage.getItem('last_seen_noti_count') || '0', 10);
            const today = new Date().toISOString().split('T')[0];

            badges.forEach(badge => {
                // 조건: 임박 식재료가 1개 이상 있고,
                // (오늘 처음 보거나 OR 내가 마지막으로 봤을 때보다 위험 식재료가 '늘어났을 때'만!)
                if (data && data.length > 0 && (lastSeenDate !== today || data.length > lastSeenCount)) {
                    badge.textContent = data.length;
                    badge.style.display = 'flex'; 
                    badge.dataset.count = data.length; // 클릭 시 저장하기 위해 임시 보관
                } else {
                    badge.style.display = 'none'; 
                }
            });
        }
    } catch (error) {
        console.error('알림 뱃지 갱신 실패:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (token) {
        checkUnreadNotifications();
    }

    const notiBtns = document.querySelectorAll('.notification-btn');
    notiBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const today = new Date().toISOString().split('T')[0];
            localStorage.setItem('last_seen_noti_date', today);
            
            // [추가] 알림을 끄는 순간의 '알림 개수'를 브라우저에 저장
            const badge = btn.querySelector('.noti-badge') || document.querySelectorAll('.noti-badge')[0];
            if (badge && badge.dataset.count) {
                localStorage.setItem('last_seen_noti_count', badge.dataset.count);
            }
            
            document.querySelectorAll('.noti-badge').forEach(b => b.style.display = 'none');
        });
    });
});