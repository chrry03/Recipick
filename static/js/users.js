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

// 1) 전역 변수
// 취향 설정 데이터
// 알러지는 고정 데이터로 유지 (변동이 적으므로)
const ALLERGIES_DATA = [
    "난류", "우유", "메밀", "땅콩", "대두", "밀", "고등어", "게", "새우", "돼지고기", 
    "복숭아", "토마토", "아황산류", "호두", "닭고기", "쇠고기", "오징어", "조개류", "잣"
];

// const INGREDIENTS_DATA = {
//     "육류": ["돼지고기", "소고기", "닭고기", "양고기"],
//     "해산물": ["새우", "게", "고등어", "오징어", "조개"],
//     "채소류": ["오이", "당근", "양파", "파프리카", "버섯", "가지", "고수", "브로콜리", "시금치", "피망", "호박", "무", "배추", "깻잎"],
//     "유제품": ["우유", "치즈", "버터"],
//     "기타": ["땅콩", "호두", "잣"]
// };

// ★ [수정] 식재료 데이터는 이제 API로 받아오므로 빈 객체로 시작하지 않고, 로직에서 처리합니다.
let currentCategoryId = 1; // 기본 카테고리 ID (채소)
const selectedAllergies = new Set();
const bannedIngredients = new Set(); // 여기에 "양파", "오이" 같은 이름이 저장됨


// ==========================================
// 2. 전역 함수 (취향 설정 페이지 onclick 대응)
// ==========================================
// 2) 초기화 및 API 호출 함수
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

// ==========================================
// [신규] API 연동 및 로직 함수들
// ==========================================

// 1. 카테고리 탭 불러오기 (화면 로드 시 실행)
async function fetchCategories() {
    const container = document.getElementById('category-wrapper');
    if (!container) return;

    try {
        const res = await fetch('/ingredients/categories/'); 
        const categories = await res.json();
        
        // 카테고리 버튼 생성
        container.innerHTML = categories.map((cat, index) => `
            <div class="category-item ${index === 0 ? 'active' : ''}" 
                 onclick="selectCategory(this, ${cat.id})">
                ${cat.icon_url || ''} ${cat.name}
            </div>
        `).join('');

        // 첫 번째 카테고리가 있으면 바로 해당 재료 불러오기
        if (categories.length > 0) {
            currentCategoryId = categories[0].id;
            fetchIngredients(currentCategoryId);
        }
    } catch (err) {
        console.error("카테고리 로드 실패:", err);
    }
}

// 2. 카테고리 클릭 시 동작
function selectCategory(el, catId) {
    document.querySelectorAll('.category-item').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    currentCategoryId = catId;
    fetchIngredients(catId);
}

// 3. 재료 목록 불러오기 (API 호출)
async function fetchIngredients(catId) {
    const container = document.getElementById('ingredient-list');
    if (!container) return;
    container.innerHTML = '<div style="padding:20px;">로딩 중...</div>';

    try {
        const res = await fetch(`/ingredients/?category_id=${catId}`);
        const ingredients = await res.json();
        renderIngredientList(ingredients);
    } catch (err) {
        console.error("식재료 로드 실패:", err);
        container.innerHTML = '<div>불러오기 실패</div>';
    }
}

// 4. 재료 검색 (엔터 쳤을 때)
async function searchIngredients(keyword) {
    if (!keyword.trim()) return;
    
    const container = document.getElementById('ingredient-list');
    container.innerHTML = '<div style="padding:20px;">검색 중...</div>';

    try {
        const res = await fetch(`/ingredients/search/?keyword=${keyword}`);
        const ingredients = await res.json();

        if (ingredients.length > 0) {
            renderIngredientList(ingredients);
        } else {
            // 검색 결과 없으면 [직접 추가] 버튼 표시
            container.innerHTML = `
                <div class="no-result" style="text-align:center; padding:20px; width:100%;">
                    <p style="margin-bottom:10px;">'${keyword}'에 대한 검색 결과가 없습니다.</p>
                    <button type="button" class="btn-mw btn-primary-mw" 
                            onclick="addCustomIngredient('${keyword}')" style="width:auto; padding: 10px 20px;">
                        '${keyword}' 직접 추가하기
                    </button>
                </div>
            `;
        }
    } catch (err) {
        console.error("검색 실패:", err);
    }
}

// 5. 화면에 재료 뿌리기 (공통 함수)
function renderIngredientList(list) {
    const container = document.getElementById('ingredient-list');
    container.innerHTML = list.map(ing => {
        // 이미 선택한 재료면 체크 표시 유지
        const isChecked = bannedIngredients.has(ing.name_ko) ? 'checked' : '';
        return `
            <label class="ing-check-item">
                <input type="checkbox" value="${ing.name_ko}" class="ing-checkbox" onchange="updateBanned(this)" ${isChecked}>
                <span>${ing.name_ko}</span>
            </label>
        `;
    }).join('');
}

// 6. 직접 추가하기 기능
function addCustomIngredient(name) {
    bannedIngredients.add(name);
    alert(`'${name}'이(가) 제외 식재료에 추가되었습니다.`);
    
    // 리스트 맨 앞에 강제로 추가해서 보여줌
    const container = document.getElementById('ingredient-list');
    const newItem = `
        <label class="ing-check-item">
            <input type="checkbox" value="${name}" class="ing-checkbox" onchange="updateBanned(this)" checked>
            <span>${name} (직접 추가)</span>
        </label>
    `;
    // 기존 내용 지우고 추가된 것만 보여주거나, 맨 위에 붙임 (여기선 맨 위 추가)
    if(container.querySelector('.no-result')) container.innerHTML = ''; // 검색결과 없음 메시지 지우기
    container.insertAdjacentHTML('afterbegin', newItem);
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
    const csrftoken = getCookie('csrftoken');

    if (!token) {
        alert("로그인이 필요합니다.");
        window.location.href = '/users/login/';
        return;
    }
    
    // ★ [수정 핵심] Serializer가 Flat 구조(write_only 필드)로 되어 있으므로
    // 'profile' 껍데기 없이 그냥 보냅니다.
    const payload = {
        cooking_level: level,
        allergies: Array.from(selectedAllergies),      // Set -> Array
        banned_ingredients: Array.from(bannedIngredients) // Set -> Array
    };

    try {
        const response = await fetch('/users/mypage/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert("취향 설정이 완료되었습니다! 메인으로 이동합니다.");
            window.location.href = "/"; 
        } else {
            const errorData = await response.json();
            console.error("저장 실패:", errorData);
            alert("저장에 실패했습니다. 다시 시도해주세요.");
        }
    } catch (error) {
        console.error("통신 오류:", error);
        alert("서버 오류가 발생했습니다.");
    }
}


// ==========================================
// 3. DOMContentLoaded 이벤트 (페이지 로드 후 실행)
// ==========================================
document.addEventListener('DOMContentLoaded', function() {

    // --- 취향 설정 페이지 초기화 ---
    const allergyContainer = document.getElementById('allergy-list');
    if (allergyContainer) {
        renderAllergies(); // 알러지는 그대로
        fetchCategories(); // ★ [신규] 카테고리 API 호출 시작!

        // ★ [신규] 검색창 이벤트 연결
        const searchInput = document.getElementById('ingredient-search');
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault(); // 폼 제출 방지
                    searchIngredients(this.value);
                }
            });
        }
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
        signupForm.addEventListener('submit', async function(e) { // async 추가 필수!
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const passwordConfirm = document.getElementById('password_confirm').value;

            // 1. 비밀번호 일치 확인
            if (password !== passwordConfirm) {
                alert('비밀번호가 일치하지 않습니다.');
                return;
            }

            // ★ 2. 이메일 중복 확인 (서버에 물어보기)
            try {
                const response = await fetch('/users/check-email/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // CSRF 토큰이 필요하다면 getCookie('csrftoken') 사용
                    },
                    body: JSON.stringify({ email: email })
                });
                
                const data = await response.json();

                // 이미 있는 이메일이면 여기서 멈춤! (다음 페이지로 안 감)
                if (!data.is_available) {
                    alert(data.message); // "이미 가입된 이메일입니다." 알림
                    return; 
                }

                // 3. 통과했으면 로컬스토리지 저장하고 이동
                localStorage.setItem('temp_email', email);
                localStorage.setItem('temp_pw', password);
                window.location.href = '/users/nickname/?next=preference';

            } catch (error) {
                console.error('이메일 확인 중 오류:', error);
                alert('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
            }
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

        } else {
            loggedInView.style.display = 'none';
            if (loggedOutView) loggedOutView.style.display = 'flex';
        }

        /* static/js/users.js 의 로그아웃 부분 수정 */

        const logoutBtn = document.getElementById('btn-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async function() { // async 추가
                if (confirm('로그아웃 하시겠습니까?')) {
                    try {
                        const refresh = localStorage.getItem('refresh_token');
                        const csrftoken = getCookie('csrftoken');

                        // ★ 1. 백엔드에 "로그아웃 할게요" 요청 (세션 삭제 + 토큰 블랙리스트)
                        // 토큰이 없더라도(이미 만료 등) 세션 로그아웃을 위해 요청은 보냅니다.
                        await fetch('/users/logout/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': csrftoken,
                                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                            },
                            body: JSON.stringify({ refresh: refresh })
                        });

                    } catch (error) {
                        console.error("로그아웃 요청 중 오류:", error);
                        // 오류가 나도 클라이언트 로그아웃은 진행
                    } finally {
                        // ★ 2. 브라우저 청소 (토큰 삭제)
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        localStorage.removeItem('user_nickname');

                        // ★ 3. 로그인 화면으로 이동
                        alert("로그아웃 되었습니다.");
                        window.location.href = '/users/login/';
                    }
                }
            });
        }
    }
});