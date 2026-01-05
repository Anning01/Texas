/**
 * 德州扑克游戏前端逻辑
 */

let ws = null;
let gameState = null;
let timerInterval = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// ============ 初始化 ============

document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    bindEvents();
    initTabs();
});

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${ROOM_ID}/${PLAYER_ID}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket 已连接');
        reconnectAttempts = 0;
        addSystemMessage('已连接到服务器');
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleMessage(message);
    };

    ws.onclose = () => {
        console.log('WebSocket 已断开');
        stopTimer();

        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            addSystemMessage(`连接断开，尝试重连 (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
            setTimeout(connectWebSocket, 2000 * reconnectAttempts);
        } else {
            addSystemMessage('无法连接到服务器，请刷新页面重试');
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
    };
}

function bindEvents() {
    document.getElementById('btn-start').addEventListener('click', () => {
        sendAction({ action: 'start_game' });
    });

    document.getElementById('btn-fold').addEventListener('click', () => {
        if (confirm('确定要弃牌吗？')) {
            sendAction({ action: 'fold' });
        }
    });

    document.getElementById('btn-check').addEventListener('click', () => {
        sendAction({ action: 'check' });
    });

    document.getElementById('btn-call').addEventListener('click', () => {
        sendAction({ action: 'call' });
    });

    document.getElementById('btn-bet').addEventListener('click', () => {
        const amount = parseInt(document.getElementById('raise-amount').value) || 0;
        sendAction({ action: 'bet', amount: amount });
    });

    document.getElementById('btn-raise').addEventListener('click', () => {
        const amount = parseInt(document.getElementById('raise-amount').value) || 0;
        sendAction({ action: 'raise', amount: amount });
    });

    document.getElementById('btn-allin').addEventListener('click', () => {
        if (confirm('确定要全押吗？')) {
            sendAction({ action: 'all_in' });
        }
    });

    document.getElementById('btn-close-modal').addEventListener('click', () => {
        document.getElementById('result-modal').style.display = 'none';
    });

    document.getElementById('btn-send').addEventListener('click', sendChat);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChat();
    });

    const slider = document.getElementById('raise-slider');
    const raiseInput = document.getElementById('raise-amount');

    slider.addEventListener('input', () => {
        raiseInput.value = slider.value;
    });

    raiseInput.addEventListener('input', () => {
        slider.value = raiseInput.value;
    });

    document.getElementById('sidebar-toggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('open');
    });

    document.querySelector('.poker-table').addEventListener('click', (e) => {
        if (e.target.closest('.sidebar') === null) {
            document.getElementById('sidebar').classList.remove('open');
        }
    });
}

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(content => {
                content.style.display = 'none';
            });
            document.getElementById(`tab-${tabName}`).style.display = 'flex';
        });
    });
}

function sendAction(action) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(action));
    }
}

function sendChat() {
    const input = document.getElementById('chat-input');
    const content = input.value.trim();
    if (content) {
        sendAction({ action: 'chat', content: content });
        input.value = '';
    }
}

// ============ 消息处理 ============

function handleMessage(message) {
    if (message.type === 'game_state') {
        gameState = message.data;
        updateUI();

        if (message.data.winners) {
            showWinners(message.data.winners);
        }
    } else if (message.type === 'chat') {
        addChatMessage(message.data);
    }
}

// ============ UI 更新 ============

function updateUI() {
    if (!gameState) return;

    updateHeader();
    updateCommunityCards();
    updatePlayers();
    updateMyHand();
    updateMyInfo();
    updateActions();
    updateTimer();
    updateActionHistory();
}

function updateHeader() {
    document.getElementById('stage').textContent = getStageText(gameState.stage);
    document.getElementById('pot').textContent = gameState.main_pot;
    document.getElementById('pot-display').textContent = gameState.main_pot;

    const blindsEl = document.getElementById('blinds');
    if (gameState.small_blind && gameState.big_blind) {
        let blindsText = `${gameState.small_blind}/${gameState.big_blind}`;
        if (gameState.ante && gameState.ante > 0) {
            blindsText += ` +${gameState.ante}`;
        }
        blindsEl.textContent = blindsText;
    }
}

function getStageText(stage) {
    const stageMap = {
        'waiting': '等待中',
        'preflop': '翻牌前',
        'flop': '翻牌',
        'turn': '转牌',
        'river': '河牌',
        'showdown': '摊牌'
    };
    return stageMap[stage] || stage;
}

function updateCommunityCards() {
    const container = document.getElementById('community-cards');
    container.innerHTML = '';

    for (let i = 0; i < 5; i++) {
        const card = gameState.community_cards[i];
        if (card) {
            const cardEl = createCardElement(card);
            cardEl.classList.add('dealing');
            container.appendChild(cardEl);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'card card-placeholder';
            container.appendChild(placeholder);
        }
    }
}

function updatePlayers() {
    const container = document.getElementById('players-area');
    container.innerHTML = '';

    // 重新排序玩家：把自己放在第一个（底部位置 position 0）
    const sortedPlayers = [...gameState.players];
    const selfIndex = sortedPlayers.findIndex(p => p.is_self);
    if (selfIndex > 0) {
        const self = sortedPlayers.splice(selfIndex, 1)[0];
        sortedPlayers.unshift(self);
    }

    // 根据玩家数量计算位置
    const numPlayers = sortedPlayers.length;
    const positions = getPlayerPositions(numPlayers);

    sortedPlayers.forEach((player, index) => {
        const seat = document.createElement('div');
        seat.className = 'player-seat';
        seat.setAttribute('data-position', positions[index]);

        if (player.is_current) seat.classList.add('is-current');
        if (player.folded) seat.classList.add('is-folded');
        if (player.is_self) seat.classList.add('is-self');

        // 徽章
        let badge = '';
        if (player.is_dealer) {
            badge = '<div class="player-badge dealer">D</div>';
        } else if (player.is_sb) {
            badge = '<div class="player-badge sb">SB</div>';
        } else if (player.is_bb) {
            badge = '<div class="player-badge bb">BB</div>';
        }

        const avatar = player.name.charAt(0).toUpperCase();

        // 手牌
        let handHtml = '';
        if (player.hand && player.hand.length > 0) {
            handHtml = '<div class="player-hand">';
            player.hand.forEach(card => {
                if (card.hidden) {
                    handHtml += '<div class="card card-back"></div>';
                } else {
                    handHtml += createCardHTML(card);
                }
            });
            handHtml += '</div>';
        }

        // 状态标签
        let statusHtml = '';
        if (player.all_in) {
            statusHtml = '<span class="player-status all-in">ALL IN</span>';
        } else if (player.folded) {
            statusHtml = '<span class="player-status folded">弃牌</span>';
        }

        seat.innerHTML = `
            <div class="player-card">
                ${badge}
                <div class="player-avatar">${avatar}</div>
                <div class="player-name">${player.name}</div>
                <div class="player-chips">${player.chips}</div>
                ${statusHtml}
                ${handHtml}
            </div>
            ${player.current_bet > 0 ? `<div class="player-bet">${player.current_bet}</div>` : ''}
        `;

        container.appendChild(seat);
    });
}

// 根据玩家数量获取位置分配 - 横向椭圆布局
function getPlayerPositions(numPlayers) {
    // 位置说明：
    // 0: 底部中央(自己) 1: 左下 2: 左中 3: 左上
    // 4: 顶部左 5: 顶部右 6: 右上 7: 右中 8: 右下
    const positionMaps = {
        2: [0, 5],           // 2人：对面
        3: [0, 3, 6],        // 3人：三角
        4: [0, 2, 5, 7],     // 4人：四角
        5: [0, 2, 4, 5, 7],  // 5人
        6: [0, 1, 3, 5, 6, 8], // 6人
        7: [0, 1, 2, 4, 5, 7, 8], // 7人
        8: [0, 1, 2, 3, 5, 6, 7, 8], // 8人
        9: [0, 1, 2, 3, 4, 5, 6, 7, 8], // 9人
        10: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] // 10人
    };
    return positionMaps[numPlayers] || positionMaps[10].slice(0, numPlayers);
}

function updateMyHand() {
    const container = document.getElementById('my-hand');
    container.innerHTML = '';

    const me = gameState.players.find(p => p.is_self);
    if (me && me.hand) {
        me.hand.forEach(card => {
            if (!card.hidden) {
                container.appendChild(createCardElement(card));
            }
        });
    }
}

function updateMyInfo() {
    const me = gameState.players.find(p => p.is_self);
    if (me) {
        document.getElementById('my-chips').textContent = me.chips;
    }
}

function updateActions() {
    const waitingActions = document.getElementById('waiting-actions');
    const gameActions = document.getElementById('game-actions');
    const btnStart = document.getElementById('btn-start');
    const waitingText = document.getElementById('waiting-text');

    const isWaiting = gameState.stage === 'waiting';
    const isShowdown = gameState.stage === 'showdown';

    if (isWaiting) {
        waitingActions.style.display = 'block';
        gameActions.style.display = 'none';

        if (gameState.is_room_owner && gameState.can_start) {
            btnStart.style.display = 'inline-block';
            waitingText.style.display = 'none';
        } else if (gameState.is_room_owner) {
            btnStart.style.display = 'none';
            waitingText.style.display = 'block';
            waitingText.textContent = '等待更多玩家（至少2人）';
        } else {
            btnStart.style.display = 'none';
            waitingText.style.display = 'block';
            waitingText.textContent = '等待房主开始游戏';
        }
    } else if (isShowdown) {
        waitingActions.style.display = 'block';
        gameActions.style.display = 'none';
        btnStart.style.display = gameState.is_room_owner ? 'inline-block' : 'none';
        btnStart.textContent = '开始下一局';
        waitingText.style.display = gameState.is_room_owner ? 'none' : 'block';
        waitingText.textContent = '等待房主开始下一局';
    } else {
        btnStart.textContent = '开始游戏';

        if (gameState.is_my_turn) {
            waitingActions.style.display = 'none';
            gameActions.style.display = 'flex';
            updateActionButtons();
        } else {
            waitingActions.style.display = 'block';
            gameActions.style.display = 'none';
            btnStart.style.display = 'none';
            waitingText.style.display = 'block';

            const currentPlayer = gameState.players.find(p => p.is_current);
            if (currentPlayer) {
                waitingText.textContent = `等待 ${currentPlayer.name} 操作...`;
            } else {
                waitingText.textContent = '等待中...';
            }
        }
    }
}

function updateActionButtons() {
    const me = gameState.players.find(p => p.is_self);
    if (!me) return;

    const btnCheck = document.getElementById('btn-check');
    const btnCall = document.getElementById('btn-call');
    const btnBet = document.getElementById('btn-bet');
    const btnRaise = document.getElementById('btn-raise');
    const callAmount = document.getElementById('call-amount');
    const raiseInput = document.getElementById('raise-amount');
    const raiseSlider = document.getElementById('raise-slider');

    const toCall = gameState.to_call || (gameState.current_bet - me.current_bet);
    const hasBetThisRound = gameState.has_bet_this_round;
    const isPreflop = gameState.stage === 'preflop';
    const canRaise = gameState.can_raise !== false;

    // 过牌/跟注
    if (toCall <= 0) {
        btnCheck.style.display = 'inline-block';
        btnCall.style.display = 'none';
    } else {
        btnCheck.style.display = 'none';
        btnCall.style.display = 'inline-block';
        callAmount.textContent = toCall;
    }

    // 下注 vs 加注
    if (isPreflop || hasBetThisRound) {
        btnBet.style.display = 'none';
        btnRaise.style.display = 'inline-block';
    } else {
        btnBet.style.display = 'inline-block';
        btnRaise.style.display = 'none';
    }

    // 加注范围
    const minAmount = gameState.min_raise || gameState.big_blind;
    const maxAmount = gameState.max_raise || me.chips;
    const isLimitMode = gameState.betting_mode === 'limit';
    const isPotLimitMode = gameState.betting_mode === 'pot_limit';

    raiseInput.value = minAmount;
    raiseInput.min = minAmount;
    raiseInput.max = maxAmount;

    if (isLimitMode) {
        // 限注模式：固定金额
        raiseSlider.style.display = 'none';
        raiseInput.readOnly = true;
        raiseInput.value = minAmount;

        if (!canRaise || maxAmount <= 0) {
            btnBet.disabled = true;
            btnRaise.disabled = true;
            btnBet.title = '已达到最大加注次数';
            btnRaise.title = '已达到最大加注次数';
        } else {
            btnBet.disabled = false;
            btnRaise.disabled = false;
            btnBet.title = '';
            btnRaise.title = '';
        }
    } else {
        // 无限注/彩池限注：显示滑块
        raiseSlider.style.display = 'block';
        raiseInput.readOnly = false;
        raiseSlider.min = minAmount;
        raiseSlider.max = maxAmount;
        raiseSlider.value = minAmount;
        btnBet.disabled = false;
        btnRaise.disabled = false;
        btnBet.title = '';
        btnRaise.title = '';

        if (isPotLimitMode) {
            btnRaise.title = `最大: ${maxAmount}`;
            btnBet.title = `最大: ${maxAmount}`;
        }
    }
}

function updateTimer() {
    const timerDisplay = document.getElementById('timer-display');
    const timerValue = document.getElementById('timer-value');

    const isWaiting = gameState.stage === 'waiting';
    const isShowdown = gameState.stage === 'showdown';

    if (isWaiting || isShowdown) {
        timerDisplay.style.display = 'none';
        stopTimer();
        return;
    }

    timerDisplay.style.display = 'flex';
    let remaining = gameState.remaining_time || 30;
    timerValue.textContent = remaining;

    stopTimer();

    if (gameState.is_my_turn) {
        timerInterval = setInterval(() => {
            remaining--;
            if (remaining <= 0) {
                remaining = 0;
                stopTimer();
            }
            timerValue.textContent = remaining;

            if (remaining <= 10) {
                timerDisplay.classList.add('warning');
            } else {
                timerDisplay.classList.remove('warning');
            }
        }, 1000);
    }
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    document.getElementById('timer-display').classList.remove('warning');
}

function updateActionHistory() {
    const container = document.getElementById('action-history');
    if (!gameState.action_history) return;

    container.innerHTML = '';
    gameState.action_history.forEach(action => {
        const item = document.createElement('div');
        item.className = 'action-item';
        item.innerHTML = `
            <span class="player">${action.player}</span>
            <span class="action">${action.action}</span>
            ${action.amount > 0 ? `<span class="amount">+${action.amount}</span>` : ''}
        `;
        container.appendChild(item);
    });

    container.scrollTop = container.scrollHeight;
}

// ============ 聊天 ============

function addChatMessage(data) {
    const container = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = `chat-message ${data.msg_type}`;

    const time = new Date(data.timestamp * 1000).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
    });

    msg.innerHTML = `
        <span class="sender">${data.player_name}:</span>
        <span class="content">${escapeHtml(data.content)}</span>
        <div class="time">${time}</div>
    `;

    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

function addSystemMessage(content) {
    addChatMessage({
        player_name: '系统',
        content: content,
        msg_type: 'system',
        timestamp: Date.now() / 1000
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ 卡牌渲染 ============

function createCardElement(card) {
    const div = document.createElement('div');
    div.className = `card ${card.color}`;
    div.innerHTML = `
        <span class="rank">${card.rank}</span>
        <span class="suit">${card.suit}</span>
    `;
    return div;
}

function createCardHTML(card) {
    return `<div class="card ${card.color}">
        <span class="rank">${card.rank}</span>
        <span class="suit">${card.suit}</span>
    </div>`;
}

// ============ 结果弹窗 ============

function showWinners(winners) {
    const modal = document.getElementById('result-modal');
    const list = document.getElementById('winners-list');

    list.innerHTML = '';

    winners.forEach(w => {
        const item = document.createElement('div');
        item.className = 'winner-item';
        item.innerHTML = `
            <div class="winner-name">${w.name}</div>
            <div class="winner-amount">+${w.amount} 筹码</div>
            <div class="winner-hand">${getHandName(w.hand_name)}</div>
        `;
        list.appendChild(item);
    });

    modal.style.display = 'flex';

    // 标记赢家
    setTimeout(() => {
        gameState.players.forEach(p => {
            if (winners.some(w => w.name === p.name)) {
                const seats = document.querySelectorAll('.player-seat');
                seats.forEach(seat => {
                    if (seat.querySelector('.player-name').textContent.includes(p.name)) {
                        seat.classList.add('is-winner');
                    }
                });
            }
        });
    }, 100);
}

function getHandName(name) {
    const handMap = {
        'HIGH_CARD': '高牌',
        'PAIR': '一对',
        'TWO_PAIR': '两对',
        'THREE_OF_KIND': '三条',
        'STRAIGHT': '顺子',
        'FLUSH': '同花',
        'FULL_HOUSE': '葫芦',
        'FOUR_OF_KIND': '四条',
        'STRAIGHT_FLUSH': '同花顺',
        'ROYAL_FLUSH': '皇家同花顺'
    };
    return handMap[name] || name || '';
}
