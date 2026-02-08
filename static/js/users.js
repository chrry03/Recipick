/* static/js/users.js - 최종 완성본 (알러지 자동 연동 포함) */

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

const ALLERGY_ICONS = {
    "난류": "eggs.png",        
    "우유": "milk.png",        
    "메밀": "buckwheat.png",
    "땅콩": "peanut.png",
    "대두": "soybean.png",
    "밀": "wheat.png",
    "고등어": "mackerel.png",
    "게": "crab.png",
    "새우": "shrimp.png",      
    "돼지고기": "pork.png",
    "복숭아": "peach.png",
    "토마토": "tomato.png",
    "아황산류": "wine.png",
    "호두": "walnut.png",
    "닭고기": "chicken.png",
    "쇠고기": "beef.png",
    "오징어": "squid.png",
    "조개류": "shellfish.png",
    "잣": "pine_nut.png"
};

// [핵심] 알러지 선택 시 자동으로 제외할 식재료 매핑
// ★ 주의: 여기에 적힌 이름이 백엔드 DB의 'name_ko'와 정확히 일치해야 자동 체크됩니다.
const ALLERGY_TO_INGREDIENTS = {
    "난류": ["달걀", "계란", "메추리알"],
    "우유": ["우유", "치즈", "요거트", "버터"],
    "땅콩": ["땅콩"],
    "대두": ["콩", "두부", "대두"],
    "밀": ["밀가루", "빵", "면", "국수"],
    "고등어": ["고등어"],
    "게": ["게", "꽃게", "대게"],
    "새우": ["새우", "대하", "칵테일새우"],
    "돼지고기": ["돼지고기", "삼겹살", "목살", "햄", "베이컨"],
    "복숭아": ["복숭아"],
    "토마토": ["토마토", "방울토마토"],
    "닭고기": ["닭고기", "치킨", "닭가슴살"],
    "쇠고기": ["소고기", "쇠고기", "차돌박이"],
    "오징어": ["오징어"],
    "조개류": ["조개", "굴", "홍합", "전복", "바지락"],
    "잣": ["잣"],
    "메밀": ["메밀"],
    "아황산류": ["와인"] 
};

// 데이터 관리 변수
let currentCategoryId = 1; 
const selectedAllergies = new Set();
const bannedIngredients = new Set(); 


// ==========================================
// 2. 전역 함수 (렌더링 및 로직)
// ==========================================

// 2-1. 알러지 렌더링
function renderAllergies() {
    const container = document.getElementById('allergy-list');
    if(!container) return;
    
    container.innerHTML = Object.keys(ALLERGY_ICONS).map(name => {
        const fileName = ALLERGY_ICONS[name];
        const imagePath = `/static/images/allergies/${fileName}`;
        
        return `
        <div class="allergy-item" onclick="toggleAllergy(this, '${name}')">
            <div class="allergy-img-box">
                <img src="${imagePath}" 
                    alt="${name}" 
                    onerror="this.style.display='none'; this.parentNode.innerText='${name[0]}'"> 
            </div>
            <div class="allergy-name">${name}</div>
        </div>
        `;
    }).join('');
}

// 2-2. 알러지 선택 토글
function toggleAllergy(el, name) {
    el.classList.toggle('selected');
    if (selectedAllergies.has(name)) selectedAllergies.delete(name);
    else selectedAllergies.add(name);
}

// 2-3. 카테고리 로드
async function fetchCategories() {
    const container = document.getElementById('category-wrapper');
    if (!container) return;

    try {
        const res = await fetch('/ingredients/categories/'); 
        const categories = await res.json();
        
        container.innerHTML = categories.map((cat, index) => `
            <div class="category-item ${index === 0 ? 'active' : ''}" 
                onclick="selectCategory(this, ${cat.id})"
                data-id="${cat.id}">  ${cat.icon_url || ''} ${cat.name}
            </div>
        `).join('');

        if (categories.length > 0) {
            currentCategoryId = categories[0].id;
            fetchIngredients(currentCategoryId);
        }
    } catch (err) {
        console.error("카테고리 로드 실패:", err);
    }
}

// 2-4. 카테고리 선택
function selectCategory(el, catId) {
    document.querySelectorAll('.category-item').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    currentCategoryId = catId;
    fetchIngredients(catId);
}

// 2-5. 식재료 목록 로드
async function fetchIngredients(catId) {
    const container = document.getElementById('ingredient-list');
    if (!container) return;
    container.innerHTML = '<div style="padding:20px; width:100%; text-align:center;">로딩 중...</div>';

    try {
        const res = await fetch(`/ingredients/?category_id=${catId}`);
        const ingredients = await res.json();
        renderIngredientList(ingredients);
    } catch (err) {
        console.error("식재료 로드 실패:", err);
        container.innerHTML = '<div style="padding:20px;">불러오기 실패</div>';
    }
}

// 2-6. 검색 기능
async function searchIngredients(keyword) {
    if (!keyword.trim()) return;
    
    const container = document.getElementById('ingredient-list');
    container.innerHTML = '<div style="padding:20px; width:100%; text-align:center;">검색 중...</div>';

    try {
        const res = await fetch(`/ingredients/search/?keyword=${keyword}`);
        const ingredients = await res.json();

        if (ingredients.length > 0) {
            renderIngredientList(ingredients);

            // 검색된 첫 번째 재료의 카테고리로 사이드바 하이라이트 변경
            if (ingredients[0].category_id) {
                const targetId = ingredients[0].category_id;
                
                document.querySelectorAll('.category-item').forEach(el => el.classList.remove('active'));
                
                const targetEl = document.querySelector(`.category-item[data-id="${targetId}"]`);
                if (targetEl) {
                    targetEl.classList.add('active');
                    targetEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }

        } else {
            alert('검색하신 재료가 없습니다');
            container.innerHTML = `
                <div style="padding:20px; width:100%; text-align:center; color:#999; font-size:14px;">
                    검색 결과가 없습니다.
                </div>
            `;
        }
    } catch (err) {
        console.error("검색 실패:", err);
        container.innerHTML = '<div style="padding:20px; text-align:center;">오류가 발생했습니다.</div>';
    }
}

// 2-7. 리스트 렌더링 (자동 체크 반영)
function renderIngredientList(list) {
    const container = document.getElementById('ingredient-list');
    container.innerHTML = list.map(ing => {
        // bannedIngredients Set에 해당 재료 이름이 있으면 checked 상태로 만듦
        const isChecked = bannedIngredients.has(ing.name_ko) ? 'checked' : '';
        
        return `
            <label class="ing-check-item">
                <input type="checkbox" value="${ing.name_ko}" class="ing-checkbox" onchange="updateBanned(this)" ${isChecked}>
                <span>${ing.name_ko}</span>
            </label>
        `;
    }).join('');
}

// 2-8. 체크박스 상태 업데이트
function updateBanned(checkbox) {
    if (checkbox.checked) bannedIngredients.add(checkbox.value);
    else bannedIngredients.delete(checkbox.value);
}

// 2-9. 전체 선택/해제
function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.ing-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    checkboxes.forEach(cb => {
        cb.checked = !allChecked;
        updateBanned(cb);
    });
}

// 2-10. 단계 이동 (알러지 -> 식재료 자동 반영 로직 포함)
function goToStep(stepNum) {
    // 1. 현재 탭 활성화 처리
    document.querySelectorAll('.step-section').forEach(el => el.classList.remove('active'));
    document.getElementById(`step-${stepNum}`).classList.add('active');

    // 2. [핵심] Step 2로 넘어갈 때 알러지 정보를 식재료 금지 목록에 반영
    if (stepNum === 2) {
        syncAllergyToBanned();
    }
}

// [핵심] 알러지 선택 정보를 제외 식재료(bannedIngredients)에 동기화
function syncAllergyToBanned() {
    selectedAllergies.forEach(allergyName => {
        // 매핑된 재료 목록 가져오기
        const targetIngredients = ALLERGY_TO_INGREDIENTS[allergyName];

        if (targetIngredients) {
            // 매핑된 재료 이름들을 bannedIngredients에 추가
            targetIngredients.forEach(ingName => bannedIngredients.add(ingName));
        } else {
            // 매핑 정보가 없으면 알러지 이름을 그대로 식재료로 간주
            bannedIngredients.add(allergyName);
        }
    });
    // (참고: 화면 갱신은 fetchIngredients나 renderIngredientList가 실행될 때 자동으로 checked 됨)
}

// 2-11. 설정 완료 및 저장
async function finishPreference(level) {
    const token = localStorage.getItem('access_token');
    const csrftoken = getCookie('csrftoken');

    if (!token) {
        alert("로그인이 필요합니다.");
        window.location.href = '/users/login/';
        return;
    }
    
    const payload = {
        cooking_level: level,
        allergies: Array.from(selectedAllergies),
        banned_ingredients: Array.from(bannedIngredients)
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
            if (response.status === 401) {
                alert("로그인 정보가 만료되었습니다. 다시 로그인해주세요.");
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/users/login/';
            } else {
                const errorData = await response.json();
                console.error("저장 실패:", errorData);
                alert("저장에 실패했습니다. (" + response.status + ")");
            }
        }
    } catch (error) {
        console.error("통신 오류:", error);
        alert("서버 오류가 발생했습니다.");
    }
}

// ==========================================
// 3. DOMContentLoaded 이벤트
// ==========================================
document.addEventListener('DOMContentLoaded', function() {

    // --- 취향 설정 페이지 초기화 ---
    const allergyContainer = document.getElementById('allergy-list');
    if (allergyContainer) {
        renderAllergies();
        fetchCategories(); // API 카테고리 로드

        // 검색창 엔터키 이벤트
        const searchInput = document.getElementById('ingredient-search');
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
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

    // --- 2. 회원가입 폼 ---
    const signupForm = document.getElementById('signup-step1-form');
    if (signupForm) {
        signupForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const passwordConfirm = document.getElementById('password_confirm').value;

            if (password !== passwordConfirm) {
                alert('비밀번호가 일치하지 않습니다.');
                return;
            }

            try {
                const response = await fetch('/users/check-email/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email })
                });
                
                const data = await response.json();

                if (!data.is_available) {
                    alert(data.message);
                    return; 
                }

                localStorage.setItem('temp_email', email);
                localStorage.setItem('temp_pw', password);
                window.location.href = '/users/nickname/?next=preference';

            } catch (error) {
                console.error('이메일 확인 중 오류:', error);
                alert('서버 오류가 발생했습니다.');
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
                    // 닉네임 변경
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

        const logoutBtn = document.getElementById('btn-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async function() {
                if (confirm('로그아웃 하시겠습니까?')) {
                    try {
                        const refresh = localStorage.getItem('refresh_token');
                        const csrftoken = getCookie('csrftoken');

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
                    } finally {
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        localStorage.removeItem('user_nickname');
                        alert("로그아웃 되었습니다.");
                        window.location.href = '/users/login/';
                    }
                }
            });
        }

        const withdrawBtn = document.getElementById('btn-withdraw');
        if (withdrawBtn) {
            withdrawBtn.addEventListener('click', async function(e) {
                e.preventDefault();
                
                if(!confirm('정말로 탈퇴하시겠습니까?\n탈퇴 시 모든 데이터가 삭제됩니다.')) {
                    return;
                }

                const token = localStorage.getItem('access_token');
                const csrftoken = getCookie('csrftoken');
                
                const requestWithdraw = async (password) => {
                    return fetch('/users/mypage/', {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`,
                            'X-CSRFToken': csrftoken
                        },
                        body: JSON.stringify({ password: password })
                    });
                };

                try {
                    let response = await requestWithdraw(null);

                    if (response.status === 400) {
                        const data = await response.json();
                        if (data.message === "비밀번호를 입력해주세요.") {
                            const password = prompt("본인 확인을 위해 비밀번호를 입력해주세요.");
                            if(!password) return;
                            response = await requestWithdraw(password);
                        }
                    }

                    if (response.status === 204) {
                        alert('탈퇴가 완료되었습니다.');
                        localStorage.clear();
                        window.location.href = '/users/login/';
                    } else {
                        const errData = await response.json();
                        alert(errData.message || '탈퇴 처리에 실패했습니다.');
                    }
                } catch (err) {
                    console.error("탈퇴 요청 오류:", err);
                    alert('서버 통신 오류가 발생했습니다.');
                }
            });
        }
    }
});