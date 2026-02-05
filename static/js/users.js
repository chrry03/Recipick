// 알림 페이지
document.addEventListener('DOMContentLoaded', function() {
    // 뒤로가기 버튼 이벤트
    const backButton = document.querySelector('.back-button');
    if (backButton) {
        backButton.addEventListener('click', function() {
            // Django에서 뒤로가기 처리
            window.history.back();
        });
    }

    // 더보기 버튼 이벤트 (모든 버튼에 적용)
    const moreButtons = document.querySelectorAll('.more-button');
    moreButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            showOptionsMenu(e, this);
        });
    });

    // 알림 아이템 클릭 이벤트
    const notificationItem = document.querySelector('.notification-item-container');
    if (notificationItem) {
        notificationItem.addEventListener('click', function() {
            // 알림 상세 페이지로 이동
            console.log('알림 클릭됨');
            // window.location.href = '/users/notification-detail/';
        });
    }
});

// 옵션 메뉴 표시 함수
function showOptionsMenu(event, buttonElement) {
    // 기존 메뉴가 있으면 제거
    const existingMenu = document.querySelector('.options-menu');
    if (existingMenu) {
        existingMenu.remove();
        return;
    }

    // 버튼이 속한 알림 아이템 컨테이너 찾기
    const notificationItem = buttonElement.closest('.notification-item-container');
    if (!notificationItem) return;

    // 새 메뉴 생성
    const menu = document.createElement('div');
    menu.className = 'options-menu';
    const notificationId = buttonElement.getAttribute('data-notification-id');
    menu.setAttribute('data-notification-id', notificationId);
    menu.innerHTML = `
        <div class="option-item" onclick="markAsRead(${notificationId})">읽음으로 표시</div>
        <div class="option-item" onclick="deleteNotification(${notificationId})">삭제</div>
    `;

    // 메뉴를 알림 아이템 컨테이너 내부에 추가 (relative positioning을 위해)
    notificationItem.appendChild(menu);

    // 위치 계산 (버튼 바로 아래)
    const buttonRect = buttonElement.getBoundingClientRect();
    const itemRect = notificationItem.getBoundingClientRect();
    
    // 버튼의 오른쪽 끝에서 메뉴의 오른쪽 끝까지의 거리
    const rightOffset = itemRect.right - buttonRect.right;

    // 스타일 추가
    menu.style.position = 'absolute';
    menu.style.right = rightOffset + 'px';
    menu.style.top = '100%';
    menu.style.marginTop = '5px';

    // 외부 클릭시 메뉴 닫기
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
    }, 0);
}

// 메뉴 닫기 함수
function closeMenu() {
    const menu = document.querySelector('.options-menu');
    if (menu) {
        menu.remove();
    }
    document.removeEventListener('click', closeMenu);
}

// 알림 삭제 함수
function deleteNotification(notificationId) {
    if (confirm('알림을 삭제하시겠습니까?')) {
        console.log('알림 삭제:', notificationId);
    }
    closeMenu();
}

// 읽음으로 표시 함수
function markAsRead(notificationId) {
    console.log('읽음으로 표시:', notificationId);
    closeMenu();
}

// CSRF 토큰 가져오기 함수
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/* static/js/users.js */

// ==========================================
// 1. 전역 유틸리티 함수 & 데이터
// ==========================================

// CSRF 토큰 가져오기
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 취향 설정 데이터
const ALLERGIES_DATA = [
    "난류", "우유", "메밀", "땅콩", "대두", "밀", "고등어", "게", "새우", "돼지고기", 
    "복숭아", "토마토", "아황산류", "호두", "닭고기", "쇠고기", "오징어", "조개류", "잣"
];

const INGREDIENTS_DATA = {
    "육류": ["돼지고기", "소고기", "닭고기", "양고기"],
    "해산물": ["새우", "게", "고등어", "오징어", "조개"],
    "채소류": ["오이", "당근", "양파", "파프리카", "버섯", "가지", "고수", "브로콜리", "시금치", "피망", "호박", "무", "배추", "깻잎"],
    "유제품": ["우유", "치즈", "버터"],
    "기타": ["땅콩", "호두", "잣"]
};

let currentCategory = "채소류";
const selectedAllergies = new Set();
const bannedIngredients = new Set();


// ==========================================
// 2. 전역 함수 (취향 설정 페이지 onclick 대응)
// ==========================================

function renderAllergies() {
    const container = document.getElementById('allergy-list');
    if(!container) return;
    
    container.innerHTML = ALLERGIES_DATA.map(name => `
        <div class="allergy-item" onclick="toggleAllergy(this, '${name}')">
            <div class="allergy-img-box">
                <img src="/static/images/ingredients/${name}.png" onerror="this.style.display='none'; this.parentNode.innerText='${name[0]}'">
            </div>
            <div class="allergy-name">${name}</div>
        </div>
    `).join('');
}

function toggleAllergy(el, name) {
    el.classList.toggle('selected');
    if (selectedAllergies.has(name)) selectedAllergies.delete(name);
    else selectedAllergies.add(name);
}

function renderIngredients(category) {
    const container = document.getElementById('ingredient-list');
    if(!container) return;
    
    const list = INGREDIENTS_DATA[category] || [];
    container.innerHTML = list.map(ing => {
        const isChecked = bannedIngredients.has(ing) ? 'checked' : '';
        return `
            <label class="ing-check-item">
                <input type="checkbox" value="${ing}" class="ing-checkbox" onchange="updateBanned(this)" ${isChecked}>
                <span>${ing}</span>
            </label>
        `;
    }).join('');
}

function setupCategoryClicks() {
    const categories = document.querySelectorAll('.category-item');
    categories.forEach(cat => {
        cat.addEventListener('click', () => {
            categories.forEach(c => c.classList.remove('active'));
            cat.classList.add('active');
            currentCategory = cat.innerText;
            renderIngredients(currentCategory);
        });
    });
}

function updateBanned(checkbox) {
    if (checkbox.checked) bannedIngredients.add(checkbox.value);
    else bannedIngredients.delete(checkbox.value);
}

function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.ing-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    checkboxes.forEach(cb => {
        cb.checked = !allChecked;
        updateBanned(cb);
    });
}

function goToStep(stepNum) {
    document.querySelectorAll('.step-section').forEach(el => el.classList.remove('active'));
    document.getElementById(`step-${stepNum}`).classList.add('active');
}

async function finishPreference(level) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        alert("로그인이 필요합니다.");
        window.location.href = '/users/login/';
        return;
    }
    
    // UI 데모용 (실제 API 연동 시 여기에 fetch 추가)
    console.log("Saving preference:", { level, allergies: [...selectedAllergies], banned: [...bannedIngredients] });
    alert("취향 설정이 완료되었습니다!");
    window.location.href = "/";
}


// ==========================================
// 3. DOMContentLoaded 이벤트 (페이지 로드 후 실행)
// ==========================================
document.addEventListener('DOMContentLoaded', function() {

    // --- 취향 설정 페이지 초기화 ---
    const allergyContainer = document.getElementById('allergy-list');
    if (allergyContainer) {
        renderAllergies();
        renderIngredients(currentCategory);
        setupCategoryClicks();
    }

    // --- 1. 로그인 폼 ---
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault(); 
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const csrftoken = getCookie('csrftoken');

            try {
                const response = await fetch('/users/login/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({ login_type: 'email', email: email, password: password })
                });
                const data = await response.json();
                if (response.ok) {
                    localStorage.setItem('access_token', data.token.access);
                    localStorage.setItem('refresh_token', data.token.refresh);
                    localStorage.setItem('user_nickname', data.user.nickname);
                    window.location.href = '/';
                } else {
                    alert(data.message || '로그인 실패');
                }
            } catch (error) {
                console.error(error);
                alert('서버 통신 오류: 서버 상태를 확인해주세요.');
            }
        });
    }

    // --- 2. 회원가입 폼 (Step 1) ---
    const signupForm = document.getElementById('signup-step1-form');
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const passwordConfirm = document.getElementById('password_confirm').value;

            if (password !== passwordConfirm) {
                alert('비밀번호가 일치하지 않습니다.');
                return;
            }
            localStorage.setItem('temp_email', email);
            localStorage.setItem('temp_pw', password);
            window.location.href = '/users/nickname/?next=preference';
        });
    }

    // --- 3. 닉네임 설정 폼 ---
    const nicknameForm = document.getElementById('nickname-form');
    if (nicknameForm) {
        nicknameForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const nickname = document.getElementById('nickname').value;
            const csrftoken = getCookie('csrftoken');
            if (!nickname) return alert('닉네임을 입력해주세요.');

            try {
                // 중복 확인
                const checkRes = await fetch(`/users/check-nickname/?nickname=${nickname}`);
                const checkData = await checkRes.json();
                if (!checkRes.ok || !checkData.is_available) {
                    alert('이미 사용 중인 닉네임입니다.');
                    return;
                }

                // 가입 또는 수정 진행
                const tempEmail = localStorage.getItem('temp_email');
                const tempPw = localStorage.getItem('temp_pw');
                const urlParams = new URLSearchParams(window.location.search);
                const nextStep = urlParams.get('next');

                if (tempEmail && tempPw) {
                    // 신규 가입
                    const signupRes = await fetch('/users/signup/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                        body: JSON.stringify({ email: tempEmail, password: tempPw, nickname: nickname })
                    });
                    const signupData = await signupRes.json();
                    if (signupRes.status === 201) {
                        alert('가입 완료!');
                        localStorage.removeItem('temp_email');
                        localStorage.removeItem('temp_pw');
                        
                        if (signupData.token) {
                            localStorage.setItem('access_token', signupData.token.access);
                            localStorage.setItem('refresh_token', signupData.token.refresh);
                        }
                        localStorage.setItem('user_nickname', nickname);
                        
                        if(nextStep === 'preference') window.location.href = '/users/preference/';
                        else window.location.href = '/';
                    } else {
                        alert(signupData.message || '가입 실패');
                    }
                } else {
                    // 닉네임 변경 (토큰 사용)
                    const token = localStorage.getItem('access_token');
                    if(token) {
                        const updateRes = await fetch('/users/mypage/', {
                            method: 'PATCH',
                            headers: { 
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${token}`,
                                'X-CSRFToken': csrftoken
                            },
                            body: JSON.stringify({ nickname: nickname })
                        });
                        if(updateRes.ok) {
                            alert('변경 완료');
                            localStorage.setItem('user_nickname', nickname);
                            window.location.href = '/users/mypage/';
                        }
                    } else {
                        alert("로그인 정보가 없습니다.");
                        window.location.href = '/users/login/';
                    }
                }
            } catch (e) {
                console.error(e);
                alert('오류 발생');
            }
        });
    }

    // --- 4. 마이페이지 로직 ---
    const loggedInView = document.getElementById('logged-in-view');
    if (loggedInView) {
        const token = localStorage.getItem('access_token');
        const loggedOutView = document.getElementById('logged-out-view');
        const nicknameDisplay = document.getElementById('display-nickname');

        if (token) {
            loggedInView.style.display = 'flex';
            if (loggedOutView) loggedOutView.style.display = 'none';
            if(nicknameDisplay) nicknameDisplay.textContent = localStorage.getItem('user_nickname') || '사용자';
            
            // 최신 정보 동기화
            fetch('/users/mypage/', { headers: { 'Authorization': `Bearer ${token}` } })
                .then(res => {
                    if (!res.ok) throw new Error('Unauthorized');
                    return res.json();
                })
                .then(data => {
                    if(data.nickname) {
                        if(nicknameDisplay) nicknameDisplay.textContent = data.nickname;
                        localStorage.setItem('user_nickname', data.nickname);
                    }
                })
                .catch(err => console.log("세션 만료 또는 오류:", err));

        } else {
            loggedInView.style.display = 'none';
            if (loggedOutView) loggedOutView.style.display = 'flex';
        }

        const logoutBtn = document.getElementById('btn-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function() {
                if (confirm('로그아웃 하시겠습니까?')) {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    localStorage.removeItem('user_nickname');
                    window.location.href = '/users/login/';
                }
            });
        }
    }
});