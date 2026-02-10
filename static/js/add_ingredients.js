/**
 * static/js/add_ingredients.js
 * 식재료 검색 및 추가 기능 (전체 탭 제거 및 수정 완료)
 */

const Utils = {
    getCsrfToken: () => document.querySelector('#csrf-token')?.dataset.token || '',
    debounce: (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    }
};

class IngredientAdder {
    constructor() {
        this.selectedItems = {}; 
        this.ownedMap = {};      
        this.currentCategory = '';
        
        this.initElements();
        if (this.container) this.init();
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
        // 초기 로드는 카테고리 로드 후 첫 번째 카테고리로 진행
    }

    attachEventListeners() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', Utils.debounce((e) => {
                this.fetchIngredients(this.currentCategory, e.target.value);
            }, 300));
        }

        this.modalCancelBtn.addEventListener('click', () => this.closeModal(this.dateModal));
        this.modalConfirmBtn.addEventListener('click', () => this.confirmSelection());
        
        if (this.noExpiryCheck) {
            this.noExpiryCheck.addEventListener('change', (e) => {
                this.expiryInput.disabled = e.target.checked;
                if(e.target.checked) this.expiryInput.value = '';
            });
        }

        if (this.directAddCancelBtn) {
            this.directAddCancelBtn.addEventListener('click', () => this.closeModal(this.directAddModal));
        }
        if (this.directAddConfirmBtn) {
            this.directAddConfirmBtn.addEventListener('click', () => this.confirmDirectAdd());
        }

        if (this.successConfirmBtn) {
            this.successConfirmBtn.addEventListener('click', () => {
                const myFridgeUrl = document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '/ingredients/my-fridge/';
                window.location.href = myFridgeUrl;
            });
        }

        if (this.submitBtn) {
            this.submitBtn.addEventListener('click', () => this.submitAll());
        }
    }

    // --- API Calls ---
    async fetchOwnedIngredients() {
        try {
            const res = await fetch('/ingredients/api/user-ingredients/?include_expired=true');
            if (res.ok) {
                const data = await res.json();
                const results = Array.isArray(data) ? data : (data.results || []);
                this.ownedMap = {};
                results.forEach(ui => { 
                    this.ownedMap[ui.ingredient] = ui.user_ingredient_id; 
                });
            }
        } catch (err) { console.error(err); }
    }

    async fetchCategories() {
        try {
            const res = await fetch('/ingredients/api/categories/'); 
            const data = await res.json();
            // 데이터 구조 확인 (results 안에 있는지 그냥 배열인지)
            const categories = Array.isArray(data) ? data : (data.results || []);
            this.renderCategories(categories);
            
            // [추가] 카테고리 로드 후 첫 번째 카테고리 자동 선택 및 로드
            if (categories.length > 0) {
                const firstCat = categories[0];
                // 카테고리 ID가 id 또는 category_id 일 수 있음
                const firstId = firstCat.id || firstCat.category_id;
                
                // 첫 번째 카테고리 활성화 UI 처리
                const firstBtn = this.categorySidebar.querySelector(`.category-item[data-id="${firstId}"]`);
                if(firstBtn) firstBtn.classList.add('active');
                
                this.currentCategory = firstId;
                this.fetchIngredients(firstId);
            }
        } catch (err) { console.error(err); }
    }

    async fetchIngredients(categoryId = '', keyword = '') {
        this.container.innerHTML = '<div class="loading-msg">로딩 중...</div>';
        try {
            // [수정 완료] URL에서 'api/list/' 제거
            let url = `/ingredients/?`; 
            if (categoryId) url += `category_id=${categoryId}&`;
            if (keyword) url += `keyword=${encodeURIComponent(keyword)}`;

            const res = await fetch(url);
            if (!res.ok) throw new Error('Network response was not ok');
            const data = await res.json();
            this.renderIngredients(Array.isArray(data) ? data : (data.results || []));
        } catch (err) {
            console.error(err);
            this.container.innerHTML = '<div class="loading-msg" style="margin-top:20px;">목록 로드 실패<br><span style="font-size:11px; color:#ccc;">(잠시 후 다시 시도해주세요)</span></div>';
        }
    }

    // --- Render ---
    renderCategories(categories) {
        let html = '';
        
        // [수정] '전체' 탭 제거함
        
        categories.forEach(cat => {
            // 카테고리 ID 처리 (id 또는 category_id)
            const catId = cat.id || cat.category_id;
            html += `<div class="category-item" data-id="${catId}">${cat.name}</div>`;
        });
        
        // 직접 추가 버튼
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
                this.categorySidebar.querySelector('.active')?.classList.remove('active');
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
            this.createCardElement(ing);
        });
    }

    createCardElement(ing) {
        const masterId = ing.id; // 이제 serializer에서 id를 보내주므로 undefined가 아님!
        const isOwned = this.ownedMap.hasOwnProperty(masterId);
        const isSelected = this.selectedItems.hasOwnProperty(masterId);

        const card = document.createElement('div');
        card.className = `ingredient-item ${isOwned || isSelected ? 'added' : ''}`;
        
        const iconHtml = ing.icon 
            ? `<img src="/static/images/icons/${ing.icon}" class="grid-icon" onerror="this.style.display='none'">` 
            : '';

        card.innerHTML = `
            <div class="checkbox-icon"></div>
            ${iconHtml}
            <span class="ingredient-name">${ing.name_ko}</span>
        `;

        card.addEventListener('click', () => this.handleItemClick(ing, card));
        
        if (typeof ing.id === 'string' && ing.id.startsWith('custom_')) {
            this.container.prepend(card);
        } else {
            this.container.appendChild(card);
        }
    }

    // --- Logic ---
    handleItemClick(ingredient, cardElement) {
        const masterId = ingredient.id;
        
        if (this.ownedMap[masterId]) {
            if (confirm('냉장고에서 삭제하시겠습니까?')) {
                this.deleteUserIngredient(this.ownedMap[masterId]).then(ok => {
                    if (ok) { delete this.ownedMap[masterId]; cardElement.classList.remove('added'); }
                });
            }
            return;
        }
        
        if (this.selectedItems[masterId]) {
            delete this.selectedItems[masterId];
            cardElement.classList.remove('added');
            this.updateCount();
            
            if (typeof masterId === 'string' && masterId.startsWith('custom_')) {
                cardElement.remove();
            }
            return;
        }
        
        this.openDateModal(ingredient, cardElement);
    }

    openDateModal(ingredient, cardElement) {
        this.currentTarget = { ingredient, cardElement };
        this.modalIngredientName.textContent = ingredient.name_ko;
        
        const date = new Date();
        date.setDate(date.getDate() + 7); 
        this.expiryInput.valueAsDate = date;
        this.expiryInput.disabled = false;
        
        if(this.noExpiryCheck) this.noExpiryCheck.checked = false;
        
        this.dateModal.classList.add('open');
    }

    openDirectAddModal() {
        this.customInput.value = '';
        this.directAddModal.classList.add('open');
        this.customInput.focus();
    }

    closeModal(modal) {
        const target = modal || this.dateModal;
        target.classList.remove('open');
        this.currentTarget = null;
    }

    confirmSelection() {
        if (!this.currentTarget) return;
        const { ingredient, cardElement } = this.currentTarget;
        
        let dateVal = this.expiryInput.value;
        if (this.noExpiryCheck.checked || !dateVal) dateVal = null;

        this.selectedItems[ingredient.id] = {
            name: ingredient.name_ko,
            category: ingredient.category_name || '기타',
            expiry_date: dateVal
        };

        cardElement.classList.add('added');
        this.updateCount();
        this.closeModal(this.dateModal);
    }

    // [직접 추가] 백엔드 저장 로직
    async confirmDirectAdd() {
        const name = this.customInput.value.trim();
        if (!name) return;
        
        try {
            // 1. 백엔드에 새 식재료 생성 요청
            const res = await fetch('/ingredients/api/custom/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': Utils.getCsrfToken()
                },
                body: JSON.stringify({ name: name })
            });

            if (!res.ok) throw new Error('저장 실패');

            // 2. 생성된 진짜 식재료 데이터 받기
            const newIngredient = await res.json(); 

            // 3. 모달 닫기
            this.closeModal(this.directAddModal);

            // 4. 화면에 카드 추가 및 즉시 선택 모달 열기
            this.createCardElement(newIngredient);
            const newCard = this.container.firstChild; 
            newCard.classList.add('added');
            
            // [중요] 생성된 재료로 소비기한 입력창 바로 띄우기
            this.openDateModal(newIngredient, newCard);

        } catch (err) {
            console.error(err);
            alert('재료 추가 중 오류가 발생했습니다.');
        }
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
            const myFridgeUrl = document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '/ingredients/my-fridge/';
            window.location.href = myFridgeUrl;
            return; 
        }
        
        try {
            const addUrl = document.querySelector('[data-add-ingredient-url]')?.dataset.addIngredientUrl || '/ingredients/add/';
            const promises = items.map(item => 
                fetch(addUrl, {
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

document.addEventListener('DOMContentLoaded', () => {
    new IngredientAdder();
});