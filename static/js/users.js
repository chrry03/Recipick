/* static/js/users.js - 카테고리 자동 전환 수정 및 최신 식재료 반영 */

// ==========================================
// 1. 전역 유틸리티 함수 & 데이터
// ==========================================

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

// [업데이트] ingredients.json 데이터를 기반으로 알러지-식재료 매핑 최신화
const ALLERGY_TO_INGREDIENTS = {
    "난류": ["달걀", "계란", "메추리알"],
    "우유": [
        "우유", "저지방 우유", "무지방 우유", "두유", 
        "요거트", "그릭요거트", "치즈", "모짜렐라 치즈", "체다 치즈", 
        "파르메산 치즈", "리코타 치즈", "크림치즈", "버터", "생크림", 
        "휘핑크림", "연유"
    ],
    "땅콩": ["땅콩"],
    "대두": [
        "대두", "콩", "검은콩", "서리태", "강낭콩", "병아리콩", "렌틸콩", 
        "완두콩", "팥", "두부", "부침두부", "찌개두부", "연두부", "순두부", 
        "콩비지", "유부", "두부면", "두부가루", "콩가루", "템페", "두유요거트", 
        "두유", "된장", "쌈장", "간장"
    ],
    "밀": [
        "밀가루", "부침가루", "튀김가루", "소면", "중면", "국수", "라면", 
        "우동면", "칼국수면", "당면", "쌀국수면", "파스타", "스파게티", "우동",
        "빵", "식빵", "빵가루", "또띠야"
    ],
    "고등어": ["고등어"],
    "게": ["게", "꽃게", "대게"],
    "새우": ["새우", "새우젓", "칵테일새우", "생새우", "건새우"],
    "돼지고기": [
        "돼지고기", "삼겹살", "목살", "앞다리살", "뒷다리살", "다진 돼지고기", 
        "햄", "스팸", "베이컨", "소시지", "살라미"
    ],
    "복숭아": ["복숭아"],
    "토마토": ["토마토", "방울토마토", "케첩", "토마토소스"],
    "닭고기": [
        "닭고기", "통닭", "닭가슴살", "닭다리", "닭다리살", "닭날개", 
        "닭봉", "닭안심", "영계", "닭가공품"
    ],
    "쇠고기": [
        "소고기", "쇠고기", "소고기 국거리", "소고기 불고기용", "샤브샤브용 소고기", 
        "등심", "안심", "채끝", "갈비", "우둔", "홍두깨", "다진 소고기", 
        "소내장", "사골", "양고기" // 양고기는 붉은 고기류라 편의상 포함 가능
    ],
    "오징어": ["오징어", "오징어채", "한치", "문어", "낙지", "주꾸미"], // 두족류 포함
    "조개류": [
        "조개", "바지락", "홍합", "꼬막", "가리비", "키조개", "전복", "굴", 
        "골뱅이", "성게", "해삼"
    ],
    "잣": ["잣"],
    "메밀": ["메밀", "메밀면"],
    "아황산류": ["와인"] 
};

let currentCategoryId = 1; 
const selectedAllergies = new Set();
const bannedIngredients = new Set(); 


// ==========================================
// 2. 전역 함수 (렌더링 및 로직)
// ==========================================

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

function toggleAllergy(el, name) {
    el.classList.toggle('selected');
    if (selectedAllergies.has(name)) selectedAllergies.delete(name);
    else selectedAllergies.add(name);
}

async function fetchCategories() {
    const container = document.getElementById('category-wrapper');
    if (!container) return;

    try {
        const res = await fetch('/ingredients/categories/'); 
        const categories = await res.json();
        
        container.innerHTML = categories.map((cat, index) => `
            <div class="category-item ${index === 0 ? 'active' : ''}" 
                onclick="selectCategory(this, ${cat.id})"
                data-id="${cat.id}">
                
                ${cat.icon_url ? `<img src="${cat.icon_url}" style="width:18px; height:18px; margin-right:4px; object-fit:contain;">` : ''}
                
                ${cat.name}
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

function selectCategory(el, catId) {
    document.querySelectorAll('.category-item').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    currentCategoryId = catId;
    fetchIngredients(catId);
}

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

// 2-6. [수정됨] 검색 기능 (카테고리 자동 전환 강화)
async function searchIngredients(keyword) {
    if (!keyword.trim()) return;
    
    const container = document.getElementById('ingredient-list');
    container.innerHTML = '<div style="padding:20px; width:100%; text-align:center;">검색 중...</div>';

    try {
        const res = await fetch(`/ingredients/search/?keyword=${keyword}`);
        const ingredients = await res.json();

        if (ingredients.length > 0) {
            renderIngredientList(ingredients);

            // [핵심] 검색 결과의 첫 번째 아이템 정보를 확인
            const firstItem = ingredients[0];
            
            // API 응답 형태에 따라 id 추출 (객체일 수도 있고, 숫자일 수도 있음)
            let targetId = null;
            if (firstItem.category) {
                targetId = (typeof firstItem.category === 'object') ? firstItem.category.id : firstItem.category;
            } else if (firstItem.category_id) {
                targetId = firstItem.category_id;
            }

            // 카테고리 ID가 확인되면 사이드바 이동
            if (targetId) {
                // 1. 모든 탭 비활성화
                document.querySelectorAll('.category-item').forEach(el => el.classList.remove('active'));
                
                // 2. 해당 ID를 가진 탭 찾기 (문자열/숫자 형변환 고려)
                const targetEl = document.querySelector(`.category-item[data-id="${targetId}"]`);
                
                if (targetEl) {
                    targetEl.classList.add('active');
                    targetEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    currentCategoryId = targetId; // 현재 상태 업데이트
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

function renderIngredientList(list) {
    const container = document.getElementById('ingredient-list');
    container.innerHTML = list.map(ing => {
        const isChecked = bannedIngredients.has(ing.name_ko) ? 'checked' : '';
        
        return `
            <label class="ing-check-item">
                <input type="checkbox" value="${ing.name_ko}" class="ing-checkbox" onchange="updateBanned(this)" ${isChecked}>
                <span>${ing.name_ko}</span>
            </label>
        `;
    }).join('');
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

    if (stepNum === 2) {
        syncAllergyToBanned();
    }
}

function syncAllergyToBanned() {
    selectedAllergies.forEach(allergyName => {
        const targetIngredients = ALLERGY_TO_INGREDIENTS[allergyName];
        if (targetIngredients) {
            targetIngredients.forEach(ingName => bannedIngredients.add(ingName));
        } else {
            bannedIngredients.add(allergyName);
        }
    });
}

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

    // ★ [추가] 소셜 로그인 토큰 처리: URL에 있는 토큰을 잡아채서 저장하기
    const urlParams = new URLSearchParams(window.location.search);
    const accessToken = urlParams.get('access');
    const refreshToken = urlParams.get('refresh');

    // ★ [추가] URL 청소하기 전에 'next' 값도 있는지 확인하고 주머니에 챙깁니다!
    const nextParam = urlParams.get('next');

    // ★ [추가] URL에서 닉네임 꺼내기
    const nicknameParam = urlParams.get('nickname');

    if (nextParam) {
        localStorage.setItem('next_step', nextParam);
    }

    // ★ [추가] 닉네임이 있으면 주머니에 저장!
    if (nicknameParam) {
        localStorage.setItem('user_nickname', nicknameParam);
    }

    if (accessToken) {
        // 1. 토큰 저장
        localStorage.setItem('access_token', accessToken);
        if (refreshToken) {
            localStorage.setItem('refresh_token', refreshToken);
        }
        
        // 2. 주소창 깔끔하게 정리 (토큰 파라미터 숨기기)
        const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
        window.history.replaceState({path: cleanUrl}, '', cleanUrl);
    }

    // --- 취향 설정 페이지 초기화 ---
    const allergyContainer = document.getElementById('allergy-list');
    if (allergyContainer) {
        renderAllergies();
        fetchCategories(); 

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

            const csrftoken = getCookie('csrftoken');

            try {
                const response = await fetch('/users/check-email/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json',
                                'X-CSRFToken': csrftoken},
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
                    // [소셜 로그인 / 기존 회원] 로직
                    const token = localStorage.getItem('access_token');

                    // ★ [수정] URL이 아니라 아까 저장해둔 localStorage에서 꺼내봅니다.
                    // (일반 회원가입은 URL에 남아있을 수 있으니 둘 다 체크하는 OR 연산자 사용)
                    const urlParams = new URLSearchParams(window.location.search);
                    const nextStep = localStorage.getItem('next_step') || urlParams.get('next');
                    
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

                            // 사용한 'next_step'은 지워주는 센스 (청소)
                            localStorage.removeItem('next_step');
                            
                            // ★ [수정] next 파라미터가 'preference'면 취향 설정으로, 아니면 메인으로!
                            if (nextStep === 'preference') {
                                window.location.href = '/users/preference/';
                            } else {
                                window.location.href = '/'; // 보통 닉네임만 바꾸면 메인으로 가는 게 자연스러움
                            }
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
        console.log("마이페이지 로직 시작!"); // ★ 추가
        const token = localStorage.getItem('access_token');
        console.log("토큰 있나요?", token);   // ★ 추가
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

