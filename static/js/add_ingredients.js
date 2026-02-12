/**
 * static/js/add_ingredients.js
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

    // [중요] HTML의 ID와 정확히 매칭
    initElements() {
        this.container = document.getElementById('ingredientGrid'); 
        this.categorySidebar = document.getElementById('categoryListContainer');
        this.searchInput = document.getElementById('searchInput');
        this.submitBtn = document.getElementById('submitBtn');
        this.countBadge = document.getElementById('countBadge');

        // 소비기한 모달
        this.dateModal = document.getElementById('dateModal');
        this.modalIngredientName = document.getElementById('modalIngredientName');
        this.expiryInput = document.getElementById('expiryInput');
        this.noExpiryCheck = document.getElementById('noExpiryCheck');
        this.modalConfirmBtn = document.getElementById('confirmBtn');
        this.modalCancelBtn = document.getElementById('cancelBtn');

        // 직접 추가 모달
        this.directAddModal = document.getElementById('directAddModal');
        this.customInput = document.getElementById('customIngredientInput');
        this.directAddConfirmBtn = document.getElementById('directAddConfirmBtn');
        this.directAddCancelBtn = document.getElementById('directAddCancelBtn');

        // 성공 모달
        this.successModal = document.getElementById('successModal');
        this.successConfirmBtn = document.getElementById('successConfirmBtn');
    }

    async init() {
        this.attachEventListeners();
        await this.fetchOwnedIngredients(); 
        await this.fetchCategories();       
    }

    attachEventListeners() {
        // 검색
        if (this.searchInput) {
            this.searchInput.addEventListener('input', Utils.debounce((e) => {
                this.fetchIngredients(this.currentCategory, e.target.value);
            }, 300));
        }

        // 소비기한 모달 버튼 연결
        if (this.modalCancelBtn) this.modalCancelBtn.addEventListener('click', () => this.closeModal(this.dateModal));
        if (this.modalConfirmBtn) this.modalConfirmBtn.addEventListener('click', () => this.confirmSelection());
        
        if (this.noExpiryCheck) {
            this.noExpiryCheck.addEventListener('change', (e) => {
                this.expiryInput.disabled = e.target.checked;
                if(e.target.checked) this.expiryInput.value = '';
            });
        }

        // 직접 추가 모달 버튼 연결
        if (this.directAddCancelBtn) {
            this.directAddCancelBtn.addEventListener('click', () => this.closeModal(this.directAddModal));
        }
        if (this.directAddConfirmBtn) {
            this.directAddConfirmBtn.addEventListener('click', () => this.confirmDirectAdd());
        }

        // 성공 모달 확인 버튼 -> 냉장고로 이동
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

    // --- API Calls (기존과 동일) ---
    async fetchOwnedIngredients() {
        try {
            const res = await fetch('/ingredients/api/user-ingredients/?include_expired=true');
            if (res.ok) {
                const data = await res.json();
                const results = Array.isArray(data) ? data : (data.results || []);
                this.ownedMap = {};
                results.forEach(ui => { this.ownedMap[ui.ingredient] = ui.user_ingredient_id; });
            }
        } catch (err) { console.error(err); }
    }

    async fetchCategories() {
        try {
            const res = await fetch('/ingredients/api/categories/'); 
            const data = await res.json();
            const categories = Array.isArray(data) ? data : (data.results || []);
            this.renderCategories(categories);
            
            if (categories.length > 0) {
                const firstCat = categories[0];
                const firstId = firstCat.id || firstCat.category_id;
                this.currentCategory = firstId;
                this.fetchIngredients(firstId);
                
                // 첫 번째 카테고리 활성화 표시
                setTimeout(() => {
                    const btn = this.categorySidebar.querySelector(`.category-item[data-id="${firstId}"]`);
                    if(btn) btn.classList.add('active');
                }, 100);
            }
        } catch (err) { console.error(err); }
    }

    async fetchIngredients(categoryId = '', keyword = '') {
        this.container.innerHTML = '<div class="loading-msg" style="text-align:center; padding:20px; color:#999; font-size:12px;">로딩 중...</div>';
        try {
            let url = `/ingredients/?`; 
            if (categoryId) url += `category_id=${categoryId}&`;
            if (keyword) url += `keyword=${encodeURIComponent(keyword)}`;

            const res = await fetch(url);
            if (!res.ok) throw new Error('Network response was not ok');
            const data = await res.json();
            this.renderIngredients(Array.isArray(data) ? data : (data.results || []));
        } catch (err) {
            console.error(err);
            this.container.innerHTML = '<div class="loading-msg">로드 실패</div>';
        }
    }

    // --- Render ---
renderCategories(categories) {
        let html = '';
        
        categories.forEach(cat => {
            // [수정] '직접 추가'를 제외하던 if문을 삭제했습니다. 이제 화면에 그려집니다!
            
            const catId = cat.id || cat.category_id;
            const iconHtml = cat.icon_url 
                ? `<img src="${cat.icon_url}" class="category-icon" alt="${cat.name}" 
                        style="width: 20px; height: 20px; margin-right: 6px; object-fit: contain;"
                        onerror="this.style.display='none'">` 
                : '';

            html += `<div class="category-item" data-id="${catId}">
                        ${iconHtml}
                        <span class="category-name">${cat.name}</span>
                     </div>`;
        });
        
        // [유지] 맨 아래에 '신규 생성용' 버튼을 별도로 붙입니다.
        html += `<div class="category-item direct-add-btn" style="justify-content: center; font-weight:bold; color: #FF7043;">
                    <span style="margin-right:5px;">+</span> 직접 추가
                 </div>`;
        
        this.categorySidebar.innerHTML = html;

        // 이벤트 리스너 연결
        this.categorySidebar.querySelectorAll('.category-item').forEach(item => {
            item.addEventListener('click', () => {
                // 1. 하단 '+ 직접 추가' 버튼 클릭 시 -> 입력 모달 열기
                if (item.classList.contains('direct-add-btn')) {
                    this.openDirectAddModal();
                    return;
                }

                // 2. 일반 카테고리(직접 추가 포함) 클릭 시 -> 해당 목록 불러오기
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
            this.container.innerHTML = '<div style="text-align:center; padding:20px; color:#999; font-size:12px;">검색 결과가 없습니다.</div>';
            return;
        }

        ingredients.forEach(ing => {
            this.createCardElement(ing);
        });
    }

    createCardElement(ing) {
        const masterId = ing.id;
        const isOwned = this.ownedMap.hasOwnProperty(masterId);
        const isSelected = this.selectedItems.hasOwnProperty(masterId);

        const card = document.createElement('div');
        card.className = `ingredient-item ${isOwned || isSelected ? 'added' : ''}`;
        
        card.innerHTML = `
            <div class="checkbox-icon"></div>
            <span class="ingredient-name">${ing.name_ko}</span>
        `;

        card.addEventListener('click', () => this.handleItemClick(ing, card));
        this.container.appendChild(card);
    }

    // --- Interaction Logic ---
    handleItemClick(ingredient, cardElement) {
        const masterId = ingredient.id;
        
        // 이미 보유 중인 경우 삭제 로직
        if (this.ownedMap[masterId]) {
            if (confirm('냉장고에서 삭제하시겠습니까?')) {
                this.deleteUserIngredient(this.ownedMap[masterId]).then(ok => {
                    if (ok) { 
                        delete this.ownedMap[masterId]; 
                        cardElement.classList.remove('added'); 
                    }
                });
            }
            return;
        }
        
        // 이미 선택한 경우 (취소)
        if (this.selectedItems[masterId]) {
            delete this.selectedItems[masterId];
            cardElement.classList.remove('added');
            this.updateCount();
            return;
        }
        
        // 새로 선택 -> 날짜 입력 모달 열기
        this.openDateModal(ingredient, cardElement);
    }

    openDateModal(ingredient, cardElement) {
        this.currentTarget = { ingredient, cardElement };
        this.modalIngredientName.textContent = ingredient.name_ko;
        
        // 기본값: 오늘 + 7일
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
        if(modal) modal.classList.remove('open');
        this.currentTarget = null;
    }

    confirmSelection() {
        if (!this.currentTarget) return;
        const { ingredient, cardElement } = this.currentTarget;
        
        let dateVal = this.expiryInput.value;
        if (this.noExpiryCheck.checked || !dateVal) dateVal = null;

        // 선택 목록에 추가
        this.selectedItems[ingredient.id] = {
            id: ingredient.id,
            name: ingredient.name_ko,
            expiry_date: dateVal
        };

        cardElement.classList.add('added');
        this.updateCount();
        this.closeModal(this.dateModal);
    }

    async confirmDirectAdd() {
        const name = this.customInput.value.trim();
        if (!name) return;
        
        try {
            const res = await fetch('/ingredients/api/custom/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': Utils.getCsrfToken()
                },
                body: JSON.stringify({ name: name })
            });

            if (!res.ok) throw new Error('저장 실패');
            const newIngredient = await res.json(); 

            this.closeModal(this.directAddModal);
            
            // 리스트에 추가하고 바로 선택 모드 진입
            this.createCardElement(newIngredient);
            const newCard = this.container.lastChild; 
            newCard.classList.add('added');
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
        
        // 1. 선택된 게 없으면 그냥 이동
        if (items.length === 0) { 
            const myFridgeUrl = document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '/ingredients/my-fridge/';
            window.location.href = myFridgeUrl;
            return; 
        }
        
        try {
            const addUrl = document.querySelector('[data-add-ingredient-url]')?.dataset.addIngredientUrl || '/ingredients/add/';
            
            // [수정] 한 번에 묶어서 보내기 (Bulk Insert)
            // views.py에서 'ingredients' 키를 확인하도록 수정했으므로 이 형식을 따라야 함
            const payload = {
                ingredients: items.map(item => ({
                    ingredient_id: item.id,
                    expire_at: item.expiry_date
                }))
            };

            // 요청은 딱 한 번만 보냅니다.
            const res = await fetch(addUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'X-CSRFToken': Utils.getCsrfToken() 
                },
                body: JSON.stringify(payload)
            });
            
            const data = await res.json();
            
            // 2. 아예 실패한 경우 (서버 에러 or 이미 꽉 참)
            if (!res.ok || (data.success === false && !data.partial)) {
                alert(data.message || '등록에 실패했습니다.');
                return; // 페이지 이동 안 함
            }

            // 3. 부분 성공 (Partial Success) - 99개 중 1개 들어가고 4개 튕김
            if (data.partial) {
                alert(data.message); // "1개만 저장되었습니다..." 메시지 출력
                
                // 부분적으로라도 저장되었으니 내 냉장고로 이동
                const myFridgeUrl = document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '/ingredients/my-fridge/';
                window.location.href = myFridgeUrl;
                return;
            }

            // 4. 완벽 성공
            this.successModal.classList.add('open');
            
        } catch (err) { 
            console.error(err);
            alert('시스템 오류가 발생했습니다.'); 
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new IngredientAdder();
});