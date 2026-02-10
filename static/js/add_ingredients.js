/**
 * static/js/add_ingredients.js
 * 식재료 검색 및 추가 기능
 */

// ==========================================
// 1. 공통 유틸리티
// ==========================================
const Utils = {
    getCsrfToken: () => {
        return document.querySelector('#csrf-token')?.getAttribute('data-token') || 
               document.querySelector('[data-csrf-token]')?.dataset.csrfToken || '';
    },
    debounce: (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    }
};

// ==========================================
// 2. IngredientAdder 클래스
// ==========================================
class IngredientAdder {
    constructor() {
        this.selectedItems = {}; 
        this.ownedMap = {};      
        this.currentCategory = '';
        
        this.initElements();
        // 컨테이너가 존재하는 페이지에서만 실행
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

        // 모달 관련
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
        // 검색창
        if (this.searchInput) {
            this.searchInput.addEventListener('input', Utils.debounce((e) => {
                this.fetchIngredients(this.currentCategory, e.target.value);
            }, 300));
        }

        // 소비기한 모달
        this.modalCancelBtn.addEventListener('click', () => this.closeModal(this.dateModal));
        this.modalConfirmBtn.addEventListener('click', () => this.confirmSelection());
        if (this.noExpiryCheck) {
            this.noExpiryCheck.addEventListener('change', (e) => {
                this.expiryInput.disabled = e.target.checked;
                if(e.target.checked) this.expiryInput.value = '';
            });
        }

        // 직접 추가 모달
        if (this.directAddCancelBtn) {
            this.directAddCancelBtn.addEventListener('click', () => this.closeModal(this.directAddModal));
        }
        if (this.directAddConfirmBtn) {
            this.directAddConfirmBtn.addEventListener('click', () => this.confirmDirectAdd());
        }

        // 성공 모달
        if (this.successConfirmBtn) {
            this.successConfirmBtn.addEventListener('click', () => {
                const myFridgeUrl = document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '/ingredients/my-fridge/';
                window.location.href = myFridgeUrl;
            });
        }

        // 등록 완료 버튼
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
            this.renderCategories(Array.isArray(data) ? data : (data.results || []));
        } catch (err) { console.error(err); }
    }

    async fetchIngredients(categoryId = '', keyword = '') {
        this.container.innerHTML = '<div class="loading-msg">로딩 중...</div>';
        try {
            let url = `/ingredients/api/list/?`;
            if (categoryId) url += `category_id=${categoryId}&`;
            if (keyword) url += `keyword=${encodeURIComponent(keyword)}`;

            const res = await fetch(url);
            const data = await res.json();
            this.renderIngredients(Array.isArray(data) ? data : (data.results || []));
        } catch (err) {
            this.container.innerHTML = '<div class="loading-msg">목록 로드 실패</div>';
        }
    }

    // --- Render ---
    renderCategories(categories) {
        let html = `<div class="category-item active" data-id="">전체</div>`;
        categories.forEach(cat => {
            html += `<div class="category-item" data-id="${cat.id}">${cat.name}</div>`;
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

            // add_ingredients.css의 .ingredient-item 클래스 사용
            const card = document.createElement('div');
            card.className = `ingredient-item ${isOwned || isSelected ? 'added' : ''}`;
            
            // 이미지 등은 CSS에서 display:none 처리됨 (리스트형)
            const iconHtml = ing.icon_name 
                ? `<img src="/static/images/icons/${ing.icon_name}" class="grid-icon" onerror="this.style.display='none'">` 
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
        
        const date = new Date();
        date.setDate(date.getDate() + 7); // 기본 7일
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
        if (this.noExpiryCheck.checked || !dateVal) {
            dateVal = null;
        }

        this.selectedItems[ingredient.id] = {
            name: ingredient.name_ko,
            category: ingredient.category_name || '기타',
            expiry_date: dateVal
        };

        cardElement.classList.add('added');
        this.updateCount();
        this.closeModal(this.dateModal);
    }

    confirmDirectAdd() {
        const name = this.customInput.value.trim();
        if (!name) return;
        
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

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    new IngredientAdder();
});