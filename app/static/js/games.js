// Minimal client-side games; each submits a score to server.
function postScore(appId, gameKey, score) {
  const tokenMeta = document.querySelector('meta[name="csrf-token"]');
  const csrf = tokenMeta ? tokenMeta.getAttribute('content') : '';
  const form = new FormData();
  form.append('game_key', gameKey);
  form.append('score', String(score));
  fetch(`/client/application/${appId}/games/submit`, {
    method: 'POST',
    body: form,
    credentials: 'same-origin',
    headers: csrf ? { 'X-CSRFToken': csrf } : {}
  })
    .then(() => window.location.reload())
    .catch(() => window.location.reload());
}

export function molaymanClickRush(appId) {
  let clicks = 0;
  let running = false;
  const btn = document.getElementById('clickRushBtn');
  const stat = document.getElementById('clickRushStat');

  btn.addEventListener('click', () => {
    if (!running) return;
    clicks++;
    stat.textContent = `Clicks: ${clicks}`;
  });

  document.getElementById('clickRushStart').addEventListener('click', () => {
    clicks = 0;
    running = true;
    stat.textContent = 'Clicks: 0 (10s)';
    setTimeout(() => {
      running = false;
      stat.textContent = `Finished: ${clicks} clicks`;
      postScore(appId, 'molayman_click_rush', clicks);
    }, 10000);
  });
}

export function molaymanReaction(appId) {
  const box = document.getElementById('reactionBox');
  const stat = document.getElementById('reactionStat');
  let start = 0;

  document.getElementById('reactionStart').addEventListener('click', () => {
    stat.textContent = 'Wait for green…';
    box.style.background = 'rgba(255,255,255,.08)';
    const delay = 700 + Math.floor(Math.random() * 1300);
    setTimeout(() => {
      start = performance.now();
      box.dataset.go = '1';
      box.style.background = 'rgba(52,211,153,.25)';
      stat.textContent = 'GO! Click the box!';
    }, delay);
  });

  box.addEventListener('click', () => {
    if (box.dataset.go !== '1') {
      stat.textContent = 'Too early. Try again.';
      return;
    }
    const ms = Math.floor(performance.now() - start);
    box.dataset.go = '0';
    box.style.background = 'rgba(255,255,255,.08)';
    stat.textContent = `Reaction: ${ms} ms`;
    postScore(appId, 'molayman_reaction', ms);
  });
}

export function molaymanLuckyNumber(appId) {
  const stat = document.getElementById('luckyStat');
  document.getElementById('luckyRoll').addEventListener('click', () => {
    const n = 1 + Math.floor(Math.random() * 100);
    stat.textContent = `Molayman number: ${n}`;
    postScore(appId, 'molayman_lucky_number', n);
  });
}

export function molaymanQuiz(appId) {
  const questions = [
    { q: 'Rajuk Uttara Model College is in…', a: 'Uttara' },
    { q: 'Discount cap is…', a: '70' },
    { q: 'Spin wheel max discount is…', a: '30' },
    { q: 'Admin name in chat is…', a: 'I am Molay Man' },
    { q: 'Website name starts with…', a: 'Molayman' }
  ];

  const qEl = document.getElementById('quizQ');
  const input = document.getElementById('quizA');
  const stat = document.getElementById('quizStat');

  let i = 0;
  let correct = 0;

  function render() {
    if (i >= questions.length) {
      stat.textContent = `Score: ${correct}/${questions.length}`;
      postScore(appId, 'molayman_quiz', correct);
      return;
    }
    qEl.textContent = questions[i].q;
    input.value = '';
    input.focus();
  }

  document.getElementById('quizStart').addEventListener('click', () => {
    i = 0; correct = 0;
    stat.textContent = 'Answer the questions…';
    render();
  });

  document.getElementById('quizSubmit').addEventListener('click', () => {
    if (i >= questions.length) return;
    const ans = (input.value || '').trim();
    if (ans.toLowerCase() === questions[i].a.toLowerCase()) correct++;
    i++;
    render();
  });
}

export function molaymanKeymaster(appId) {
  const target = document.getElementById('keyTarget');
  const stat = document.getElementById('keyStat');
  let score = 0;
  let remaining = 0;

  function tick() {
    if (remaining <= 0) {
      stat.textContent = `Finished: ${score}`;
      postScore(appId, 'molayman_keymaster', score);
      return;
    }
    remaining--;
    target.textContent = `Type: ${String.fromCharCode(65 + Math.floor(Math.random() * 26))}`;
    target.dataset.char = target.textContent.slice(-1);
    document.getElementById('keyTimer').textContent = `${remaining}s`;
    setTimeout(tick, 1000);
  }

  document.getElementById('keyStart').addEventListener('click', () => {
    score = 0;
    remaining = 20;
    stat.textContent = 'Go!';
    tick();
  });

  document.addEventListener('keydown', (e) => {
    if (remaining <= 0) return;
    if ((e.key || '').toUpperCase() === target.dataset.char) {
      score += 5;
      stat.textContent = `Score: ${score}`;
    }
  });
}

export function molaymanMemory(appId) {
  const grid = document.getElementById('memGrid');
  const stat = document.getElementById('memStat');

  const icons = ['★','◆','●','▲','♥','♣','☀','☾'];
  let cards = [];
  let first = null;
  let lock = false;
  let matches = 0;

  function setup() {
    matches = 0;
    first = null;
    lock = false;
    const base = icons.concat(icons);
    base.sort(() => Math.random() - 0.5);
    cards = base.map((v, idx) => ({ idx, v, open: false, done: false }));

    grid.innerHTML = '';
    for (const c of cards) {
      const el = document.createElement('button');
      el.className = 'card rounded-xl p-4 text-xl text-white/90 hover:brightness-110';
      el.textContent = '□';
      el.addEventListener('click', () => flip(c, el));
      grid.appendChild(el);
      c.el = el;
    }
    stat.textContent = 'Matches: 0/8';
  }

  function reveal(c) { c.open = true; c.el.textContent = c.v; }
  function hide(c) { c.open = false; c.el.textContent = '□'; }

  function flip(c) {
    if (lock || c.done || c.open) return;
    reveal(c);
    if (!first) { first = c; return; }
    lock = true;
    if (first.v === c.v) {
      first.done = true; c.done = true;
      matches++;
      stat.textContent = `Matches: ${matches}/8`;
      first = null;
      lock = false;
      if (matches >= 8) {
        postScore(appId, 'molayman_memory', matches);
      }
      return;
    }
    setTimeout(() => {
      hide(first); hide(c);
      first = null;
      lock = false;
    }, 650);
  }

  document.getElementById('memStart').addEventListener('click', setup);
}

export function molaymanMathSprint(appId) {
  const q = document.getElementById('mathQ');
  const input = document.getElementById('mathA');
  const stat = document.getElementById('mathStat');
  let a = 0, b = 0;
  let correct = 0;
  let total = 0;
  let running = false;
  let timer = null;

  function nextQ() {
    a = 1 + Math.floor(Math.random() * 20);
    b = 1 + Math.floor(Math.random() * 20);
    q.textContent = `${a} + ${b} = ?`;
    input.value = '';
    input.focus();
  }

  function stop() {
    running = false;
    if (timer) clearTimeout(timer);
    stat.textContent = `Finished: ${correct} correct`;
    postScore(appId, 'molayman_math_sprint', correct);
  }

  document.getElementById('mathStart').addEventListener('click', () => {
    correct = 0; total = 0; running = true;
    stat.textContent = '15s… answer fast!';
    nextQ();
    timer = setTimeout(stop, 15000);
  });

  document.getElementById('mathSubmit').addEventListener('click', () => {
    if (!running) return;
    const ans = parseInt(input.value, 10);
    if (!Number.isNaN(ans) && ans === (a + b)) correct++;
    total++;
    stat.textContent = `Correct: ${correct} / ${total}`;
    nextQ();
  });
}

export function molaymanCoinFlip(appId) {
  const stat = document.getElementById('coinStat');
  let rounds = 0;
  let correct = 0;

  function play(guess) {
    if (rounds >= 10) return;
    const flip = Math.random() < 0.5 ? 'heads' : 'tails';
    rounds++;
    if (guess === flip) correct++;
    stat.textContent = `Round ${rounds}/10 • Flip: ${flip} • Correct: ${correct}`;
    if (rounds >= 10) {
      postScore(appId, 'molayman_coin_flip', correct);
    }
  }

  document.getElementById('coinStart').addEventListener('click', () => {
    rounds = 0; correct = 0;
    stat.textContent = 'Round 0/10 • Choose heads or tails';
  });
  document.getElementById('coinHeads').addEventListener('click', () => play('heads'));
  document.getElementById('coinTails').addEventListener('click', () => play('tails'));
}

export function molaymanSliderPrecision(appId) {
  const stat = document.getElementById('sliderStat');
  const slider = document.getElementById('sliderInput');
  const targetEl = document.getElementById('sliderTarget');
  let target = 50;

  function newTarget() {
    target = 1 + Math.floor(Math.random() * 100);
    targetEl.textContent = String(target);
    slider.value = 50;
    stat.textContent = 'Move slider close to target and submit.';
  }

  document.getElementById('sliderStart').addEventListener('click', newTarget);
  document.getElementById('sliderSubmit').addEventListener('click', () => {
    const v = parseInt(slider.value, 10);
    const error = Math.abs(v - target);
    stat.textContent = `Your value: ${v} • Error: ${error}`;
    // Lower error is better; send "100 - error" as score.
    postScore(appId, 'molayman_slider_precision', Math.max(0, 100 - error));
  });
}

export function molaymanWordScramble(appId) {
  const words = [
    { w: 'MOLAYMAN', s: 'YAMMALON' },
    { w: 'LOTTERY', s: 'YRTTLOE' },
    { w: 'ADMISSION', s: 'NOMISDASI' },
    { w: 'UTTARA', s: 'TTAURA' },
    { w: 'COLLEGE', s: 'LGELOEC' }
  ];

  const scr = document.getElementById('scrWord');
  const input = document.getElementById('scrA');
  const stat = document.getElementById('scrStat');
  let i = 0;
  let correct = 0;

  function render() {
    if (i >= words.length) {
      stat.textContent = `Finished: ${correct}/${words.length}`;
      postScore(appId, 'molayman_word_scramble', correct);
      return;
    }
    scr.textContent = words[i].s;
    input.value = '';
    input.focus();
  }

  document.getElementById('scrStart').addEventListener('click', () => {
    i = 0; correct = 0;
    stat.textContent = 'Unscramble the words…';
    render();
  });
  document.getElementById('scrSubmit').addEventListener('click', () => {
    if (i >= words.length) return;
    const ans = (input.value || '').trim().toUpperCase();
    if (ans === words[i].w) correct++;
    i++;
    render();
  });
}

export function molaymanTimingTap(appId) {
  const bar = document.getElementById('tapBar');
  const stat = document.getElementById('tapStat');
  let t = 0;
  let dir = 1;
  let raf = null;
  let taps = 0;
  let points = 0;

  function step() {
    t += dir * 0.018;
    if (t >= 1) { t = 1; dir = -1; }
    if (t <= 0) { t = 0; dir = 1; }
    bar.style.width = `${Math.floor(t * 100)}%`;
    raf = requestAnimationFrame(step);
  }

  function reset() {
    t = 0; dir = 1; taps = 0; points = 0;
    bar.style.width = '0%';
    stat.textContent = 'Tap when the bar is near 100% (10 taps).';
  }

  document.getElementById('tapStart').addEventListener('click', () => {
    reset();
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(step);
  });

  document.getElementById('tapBtn').addEventListener('click', () => {
    if (!raf) return;
    taps++;
    const pct = Math.floor(t * 100);
    if (pct >= 90) points++;
    stat.textContent = `Tap ${taps}/10 • Hit: ${pct}% • Points: ${points}`;
    if (taps >= 10) {
      cancelAnimationFrame(raf);
      raf = null;
      postScore(appId, 'molayman_timing_tap', points);
    }
  });
}

export function molaymanColorMatch(appId) {
  const colors = [
    { name: 'RED', css: '#ef4444' },
    { name: 'GREEN', css: '#22c55e' },
    { name: 'BLUE', css: '#3b82f6' },
    { name: 'PURPLE', css: '#a855f7' },
  ];

  const word = document.getElementById('colorWord');
  const stat = document.getElementById('colorStat');
  let rounds = 0;
  let correct = 0;
  let answer = '';

  function newRound() {
    const w = colors[Math.floor(Math.random() * colors.length)];
    const c = colors[Math.floor(Math.random() * colors.length)];
    word.textContent = w.name;
    word.style.color = c.css;
    answer = c.name;
  }

  function choose(name) {
    if (rounds >= 8) return;
    rounds++;
    if (name === answer) correct++;
    stat.textContent = `Round ${rounds}/8 • Correct: ${correct}`;
    if (rounds >= 8) {
      postScore(appId, 'molayman_color_match', correct);
      return;
    }
    newRound();
  }

  document.getElementById('colorStart').addEventListener('click', () => {
    rounds = 0; correct = 0;
    stat.textContent = 'Pick the COLOR of the text (not the word).';
    newRound();
  });

  document.getElementById('colorRed').addEventListener('click', () => choose('RED'));
  document.getElementById('colorGreen').addEventListener('click', () => choose('GREEN'));
  document.getElementById('colorBlue').addEventListener('click', () => choose('BLUE'));
  document.getElementById('colorPurple').addEventListener('click', () => choose('PURPLE'));
}
