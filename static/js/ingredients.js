/**
 * Ingredients API Client
 * - Pagination(results) 대응 추가
 * - Serializer 필드명 매칭 (user_ingredient_id, ingredient_name 등)
 */

(function() {
    'use strict';

    // ==========================================
    // 공통 유틸리티
    // ==========================================
    const Utils = {
        getCsrfToken() {
            const el = document.querySelector('[data-csrf-token]');
            return el ? el.dataset.csrfToken : this.getCookie('csrftoken');
        },
        getCookie(name) {
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
        },
        // [수정] D-Day 계산 함수 (Utils)
        calculateDday(expiryDateStr) {
            // 날짜가 없으면 (소비기한 미입력)
            if (!expiryDateStr) return { label: '-', isUrgent: false, text: '' };
            
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const expiry = new Date(expiryDateStr);
            expiry.setHours(0, 0, 0, 0);

            const diffTime = expiry - today;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays < 0) return { label: '만료', isUrgent: true, text: '만료' }; 
            if (diffDays === 0) return { label: 'D-Day', isUrgent: true, text: '오늘' };
            
            const isUrgent = diffDays <= 3;
            return { label: `D-${diffDays}`, isUrgent: isUrgent, text: `${diffDays}일 전` };
        },
        debounce(func, wait) {
            let timeout;
            return function(...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        }
    };

    // ==========================================
    // 1. 식재료 등록 화면 (IngredientAdder)
    // ==========================================
    class IngredientAdder {
        constructor() {
            this.selectedItems = {}; 
            this.ownedMap = {};      
            this.currentCategory = '';
            
            this.initElements();
            if (this.container) {
                this.init();
            }
        }

        initElements() {
            this.container = document.getElementById('ingredientGrid'); 
            this.categorySidebar = document.getElementById('categoryListContainer');
            this.searchInput = document.getElementById('searchInput');
            this.submitBtn = document.getElementById('submitBtn');
            this.countBadge = document.getElementById('countBadge');

            this.dateModal = document.getElementById('dateModal');
            this.modalIngredientName = document.getElementById('modalIngredientName');
            this.expiryInput = document.getElementById('expiryInput');
            this.noExpiryCheck = document.getElementById('noExpiryCheck');
            this.modalConfirmBtn = document.getElementById('confirmBtn');
            this.modalCancelBtn = document.getElementById('cancelBtn');

            this.directAddModal = document.getElementById('directAddModal');
            this.customInput = document.getElementById('customIngredientInput');
            this.directAddConfirmBtn = document.getElementById('directAddConfirmBtn');
            this.directAddCancelBtn = document.getElementById('directAddCancelBtn');

            this.successModal = document.getElementById('successModal');
            this.successConfirmBtn = document.getElementById('successConfirmBtn');
        }

        async init() {
            this.attachEventListeners();
            await this.fetchOwnedIngredients(); 
            await this.fetchCategories();       
            await this.fetchIngredients();      
        }

        attachEventListeners() {
            this.searchInput.addEventListener('input', Utils.debounce((e) => {
                this.fetchIngredients(this.currentCategory, e.target.value);
            }, 300));

            this.modalCancelBtn.addEventListener('click', () => this.closeModal(this.dateModal));
            this.modalConfirmBtn.addEventListener('click', () => this.confirmSelection());
            if (this.noExpiryCheck) {
                this.noExpiryCheck.addEventListener('change', (e) => {
                    this.expiryInput.disabled = e.target.checked;
                    if(e.target.checked) this.expiryInput.value = '';
                });
            }

            this.directAddCancelBtn.addEventListener('click', () => this.closeModal(this.directAddModal));
            this.directAddConfirmBtn.addEventListener('click', () => this.confirmDirectAdd());

            this.successConfirmBtn.addEventListener('click', () => {
                window.location.href = '/ingredients/my-fridge/';
            });

            this.submitBtn.addEventListener('click', () => this.submitAll());
        }

        // --- API Calls ---
        async fetchOwnedIngredients() {
            try {
                const res = await fetch('/ingredients/api/user-ingredients/?include_expired=true');
                if (res.ok) {
                    const data = await res.json();
                    // [핵심 수정] DRF Pagination 대응 (results 키 확인)
                    const results = Array.isArray(data) ? data : (data.results || []);
                    
                    this.ownedMap = {};
                    results.forEach(ui => { 
                        // ui.ingredient는 ID(int)입니다.
                        this.ownedMap[ui.ingredient] = ui.user_ingredient_id; 
                    });
                }
            } catch (err) { console.error(err); }
        }

        async fetchCategories() {
            try {
                const res = await fetch('/ingredients/categories/'); 
                const data = await res.json();
                this.renderCategories(Array.isArray(data) ? data : (data.results || []));
            } catch (err) { console.error(err); }
        }

        async fetchIngredients(categoryId = '', keyword = '') {
            this.container.innerHTML = '<div class="loading-msg">로딩 중...</div>';
            try {
                let url = `/ingredients/?`;
                if (categoryId) url += `category_id=${categoryId}&`;
                if (keyword) url += `keyword=${encodeURIComponent(keyword)}`;

                const res = await fetch(url);
                const data = await res.json();
                this.renderIngredients(Array.isArray(data) ? data : (data.results || []));
            } catch (err) {
                this.container.innerHTML = '<div class="loading-msg">목록 로드 실패</div>';
            }
        }

        // ... (fetchIngredients 메서드 뒤에 이어서 붙여넣기) ...

        // --- Render ---
        renderCategories(categories) {
            let html = `<div class="category-item active" data-id="">전체</div>`;
            categories.forEach(cat => {
                html += `<div class="category-item" data-id="${cat.id}">${cat.name}</div>`;
            });
            html += `<div class="category-item direct-add-btn" style="color: #FF7043; font-weight:bold;">
                        <span style="margin-right:5px;">+</span> 직접 추가
                     </div>`;
            this.categorySidebar.innerHTML = html;

            this.categorySidebar.querySelectorAll('.category-item').forEach(item => {
                item.addEventListener('click', () => {
                    if (item.classList.contains('direct-add-btn')) {
                        this.openDirectAddModal();
                        return;
                    }
                    this.categorySidebar.querySelector('.active').classList.remove('active');
                    item.classList.add('active');
                    this.currentCategory = item.dataset.id;
                    this.fetchIngredients(this.currentCategory, this.searchInput.value);
                });
            });
        }

        renderIngredients(ingredients) {
            this.container.innerHTML = '';
            if (!ingredients || ingredients.length === 0) {
                this.container.innerHTML = '<div class="loading-msg">검색 결과가 없습니다.</div>';
                return;
            }

            ingredients.forEach(ing => {
                const masterId = ing.id;
                const isOwned = this.ownedMap.hasOwnProperty(masterId);
                const isSelected = this.selectedItems.hasOwnProperty(masterId);

                const card = document.createElement('div');
                card.className = `ingredient-item ${isOwned || isSelected ? 'added' : ''}`;
                
                // 아이콘 처리 (없으면 기본값)
                const iconHtml = ing.icon_name 
                    ? `<img src="/static/images/ingredients/${ing.icon_name}" class="ingredient-img" onerror="this.style.display='none'">` 
                    : '';

                card.innerHTML = `
                    <div class="checkbox-icon"></div>
                    ${iconHtml}
                    <span class="ingredient-name">${ing.name_ko}</span>
                `;

                card.addEventListener('click', () => this.handleItemClick(ing, card));
                this.container.appendChild(card);
            });
        }

        // --- Logic ---
        handleItemClick(ingredient, cardElement) {
            const masterId = ingredient.id;
            
            // 1. 이미 보유중 (삭제 요청)
            if (this.ownedMap[masterId]) {
                if (confirm('냉장고에서 삭제하시겠습니까?')) {
                    this.deleteUserIngredient(this.ownedMap[masterId]).then(ok => {
                        if (ok) { delete this.ownedMap[masterId]; cardElement.classList.remove('added'); }
                    });
                }
                return;
            }
            // 2. 선택 취소
            if (this.selectedItems[masterId]) {
                delete this.selectedItems[masterId];
                cardElement.classList.remove('added');
                this.updateCount();
                return;
            }
            // 3. 선택 (모달 열기)
            this.openDateModal(ingredient, cardElement);
        }

        openDateModal(ingredient, cardElement) {
            this.currentTarget = { ingredient, cardElement };
            this.modalIngredientName.textContent = ingredient.name_ko;
            
            // 날짜 초기화 (오늘 + 7일)
            const date = new Date();
            date.setDate(date.getDate() + 7);
            this.expiryInput.valueAsDate = date;
            this.expiryInput.disabled = false;
            
            if(this.noExpiryCheck) this.noExpiryCheck.checked = false;
            
            // 모달 열기 (editModal 대신 dateModal 사용 확인)
            this.dateModal.classList.add('open');
        }

        openDirectAddModal() {
            this.customInput.value = '';
            this.directAddModal.classList.add('open');
            this.customInput.focus();
        }

        closeModal(modal) {
            // 인자가 없으면 dateModal 닫기
            const target = modal || this.dateModal;
            target.classList.remove('open');
            this.currentTarget = null;
        }

        // [중요] 소비기한 입력 확인 및 데이터 저장
        confirmSelection() {
            if (!this.currentTarget) return;
            const { ingredient, cardElement } = this.currentTarget;
            
            // 날짜 값 처리 (체크박스 체크 시 또는 값 없을 시 null)
            let dateVal = this.expiryInput.value;
            if (this.noExpiryCheck.checked || !dateVal) {
                dateVal = null;
            }

            // 데이터 저장
            this.selectedItems[ingredient.id] = {
                name: ingredient.name_ko,
                // category는 ID 또는 이름일 수 있음. 안전하게 문자열 변환
                category: ingredient.category ? ingredient.category.name : '기타',
                expiry_date: dateVal
            };

            cardElement.classList.add('added');
            this.updateCount();
            this.closeModal(this.dateModal);
        }

        // 직접 추가 확인
        confirmDirectAdd() {
            const name = this.customInput.value.trim();
            if (!name) return;
            
            // 임시 ID 생성
            const tempId = `custom_${Date.now()}`;
            this.selectedItems[tempId] = { 
                name: name, 
                category: '기타', 
                expiry_date: null 
            };
            
            this.updateCount();
            this.closeModal(this.directAddModal);
            alert(`'${name}'이(가) 선택 목록에 추가되었습니다.`);
        }

        updateCount() {
            const count = Object.keys(this.selectedItems).length;
            this.countBadge.innerText = count > 0 ? `(${count})` : '';
        }

        async deleteUserIngredient(id) {
            try {
                await fetch(`/ingredients/api/user-ingredients/${id}/`, { 
                    method: 'DELETE', 
                    headers: { 'X-CSRFToken': Utils.getCsrfToken() } 
                });
                return true;
            } catch (e) { return false; }
        }

        async submitAll() {
            const items = Object.values(this.selectedItems);
            if (items.length === 0) { 
                alert('추가할 식재료가 없습니다.'); 
                return; 
            }
            try {
                // views.py의 add_ingredient_view로 POST 전송
                // 구조: { added: [ ... ] }
                const promises = items.map(item => 
                    fetch('/ingredients/add/', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json', 
                            'X-CSRFToken': Utils.getCsrfToken() 
                        },
                        body: JSON.stringify({ added: [item] })
                    })
                );
                await Promise.all(promises);
                this.successModal.classList.add('open');
            } catch (err) { 
                console.error(err);
                alert('등록 중 오류가 발생했습니다.'); 
            }
        }
    }

    // ==========================================
    // 2. 내 냉장고 화면 (MyFridgeManager)
    // ==========================================
    class MyFridgeManager {
        constructor() {
            this.ingredients = []; 
            this.currentFilter = '전체';
            this.initElements();
            if (this.mainContainer) {
                this.init();
            }
        }

        initElements() {
            this.mainContainer = document.querySelector('.my-fridge-card'); 
            this.shelfContainer = document.getElementById('fridgeShelf');   
            this.emptyState = document.querySelector('.empty-state-container');
            this.filterBar = document.querySelector('.filter-bar');

            this.editModal = document.getElementById('editModal');
            this.modalTitle = document.getElementById('modalIngredientName');
            this.expiryInput = document.getElementById('expiryInput');
            this.cancelBtn = document.getElementById('cancelBtn');
            this.confirmBtn = document.getElementById('confirmBtn');
        }

        async init() {
            this.attachEventListeners();
            await this.fetchMyIngredients();
        }

        attachEventListeners() {
            if (this.cancelBtn) this.cancelBtn.addEventListener('click', () => this.closeModal());
            if (this.confirmBtn) this.confirmBtn.addEventListener('click', () => this.updateIngredient());
        }

        async fetchMyIngredients() {
            // 로딩 중 표시 (CSS로 중앙 정렬됨)
            if(this.shelfContainer) this.shelfContainer.innerHTML = '<div class="loading-msg">냉장고를 여는 중...</div>';
            
            try {
                const res = await fetch('/ingredients/api/user-ingredients/');
                if (res.ok) {
                    const data = await res.json();
                    // [핵심 수정] DRF Pagination 대응: results가 있으면 그것을, 없으면 data 자체를 사용
                    this.ingredients = Array.isArray(data) ? data : (data.results || []);
                    this.render();
                } else {
                    console.error('불러오기 실패:', res.status);
                    this.shelfContainer.innerHTML = '<div class="loading-msg">데이터를 불러오지 못했습니다.</div>';
                }
            } catch (err) {
                console.error(err);
                this.shelfContainer.innerHTML = '<div class="loading-msg">오류가 발생했습니다.</div>';
            }
        }

        render() {
            // 1. 빈 냉장고 체크
            if (!this.ingredients || this.ingredients.length === 0) {
                if (this.emptyState) this.emptyState.style.display = 'flex';
                if (this.mainContainer) this.mainContainer.style.display = 'none';
                if (this.filterBar) this.filterBar.style.display = 'none';
                return;
            }

            // 2. 데이터 있음
            if (this.emptyState) this.emptyState.style.display = 'none';
            if (this.mainContainer) this.mainContainer.style.display = 'block';
            if (this.filterBar) this.filterBar.style.display = 'flex';

            this.renderFilterBar();
            this.renderShelf(this.currentFilter);
        }

        renderFilterBar() {
            const counts = { '전체': this.ingredients.length };
            this.ingredients.forEach(item => {
                const cat = item.category_name || '기타'; // Serializer field name
                counts[cat] = (counts[cat] || 0) + 1;
            });

            const categories = Object.keys(counts).sort((a, b) => a === '전체' ? -1 : 1);
            
            let html = '';
            categories.forEach(cat => {
                const isActive = this.currentFilter === cat ? 'active' : '';
                html += `
                    <div class="filter-chip ${isActive}" data-category="${cat}">
                        ${cat}<span class="count">(${counts[cat]})</span>
                    </div>
                `;
            });
            
            this.filterBar.innerHTML = html;

            this.filterBar.querySelectorAll('.filter-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    this.currentFilter = chip.dataset.category;
                    this.renderFilterBar(); 
                    this.renderShelf(this.currentFilter);
                });
            });
        }

        renderShelf(filterCategory) {
            const filtered = filterCategory === '전체' 
                ? this.ingredients 
                : this.ingredients.filter(item => {
                    const cat = item.category_name || '기타';
                    return cat === filterCategory;
                });

            this.shelfContainer.innerHTML = '';
            
            filtered.forEach(ui => {
                const dDay = Utils.calculateDday(ui.expire_at);
                const isUrgent = dDay.isUrgent; 
                const badgeStyle = isUrgent ? 'color:#D32F2F; font-weight:bold;' : 'color:#555;';
                
                const itemDiv = document.createElement('div');
                itemDiv.className = 'fridge-item';
                
                // 아이콘 처리: DB에 icon URL이 있으면 사용, 없으면 기본 이모지
                const iconContent = ui.icon 
                    ? `<img src="${ui.icon}" class="ingredient-img" alt="${ui.ingredient_name}" style="width:100%;height:100%;object-fit:contain;">` 
                    : '🍽️';

                itemDiv.innerHTML = `
                    <div class="grid-content">
                        <div class="item-icon-box ${isUrgent ? 'urgent' : ''}">
                            <div class="d-day-badge" style="${badgeStyle}">
                                ${dDay.label}
                            </div>
                            <div class="emoji-icon" style="font-size:30px; width:100%; height:100%; display:flex; align-items:center; justify-content:center;">
                                ${iconContent}
                            </div>
                        </div>
                        <div class="shelf-deco"></div>
                        <span class="item-name">${ui.ingredient_name}</span>
                    </div>
                `;

                itemDiv.addEventListener('click', () => this.openEditModal(ui));
                this.shelfContainer.appendChild(itemDiv);
            });
        }

        openEditModal(userIngredient) {
            // [중요] Serializer의 PK 필드명: user_ingredient_id
            this.currentTargetId = userIngredient.user_ingredient_id;
            this.modalTitle.textContent = userIngredient.ingredient_name; 
            this.expiryInput.value = userIngredient.expire_at || ''; 
            this.editModal.classList.add('open');
        }

        closeModal() {
            this.editModal.classList.remove('open');
            this.currentTargetId = null;
        }

        async updateIngredient() {
            if (!this.currentTargetId) return;
            const newDate = this.expiryInput.value;
            
            try {
                const res = await fetch(`/ingredients/api/user-ingredients/${this.currentTargetId}/`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': Utils.getCsrfToken()
                    },
                    body: JSON.stringify({ expire_at: newDate || null })
                });

                if (res.ok) {
                    this.closeModal();
                    await this.fetchMyIngredients(); // 목록 갱신
                } else {
                    alert('수정 실패');
                }
            } catch (err) {
                console.error(err);
                alert('오류 발생');
            }
        }
    }

    // ==========================================
    // 초기화
    // ==========================================
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('ingredientGrid')) {
            new IngredientAdder();
        }
        if (document.querySelector('.my-fridge-card') || document.querySelector('.empty-state-container')) {
            new MyFridgeManager();
        }
    });

})();