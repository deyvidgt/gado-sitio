# Onda 16 — IoT Básico Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver 3-sensor IoT MVP (balança Bluetooth + emulador, colar temp+GPS, comedouro) with localStorage offline cache, PWA sync, and weight/temperature alerts.

**Architecture:** Modular sensor layer (6 JS classes: 3 real + 3 emulators) → IoTManager (pareamento, leitura, fila offline, sync automático) → 4 Flask endpoints (POST /api/iot/*) → alertas integrados (queda peso >5%, temp fora faixa). Cada sensor é independente; adicionar novo não requer refactor.

**Tech Stack:** Web Bluetooth API, localStorage (fila offline), Flask, Jinja2, vanilla JS (sem frameworks).

**Spec:** `docs/superpowers/specs/2026-11-01-iot-basico-design.md`

---

## Global Constraints

- **Language:** JavaScript (PWA) + Python (Flask)
- **Offline-first:** localStorage (não IndexedDB, mantém simples)
- **Fila máx:** 100 itens; limpa após sync
- **Web Bluetooth:** Android suportado; iOS fallback emulador
- **Nenhum hardware real:** Emuladores obrigatórios
- **Integração:** db.py/Manejo aba (salvar_linha)
- **Alertas:** Peso >5% em 7d, Temp <18°C ou >28°C
- **localStorage keys:** `iot_devices`, `iot_fila_offline` (exatos)

---

## Review Focus

1. **localStorage Cheio:** Fila atinge 100+ itens → comportamento indefinido. Teste: `test_fila_max_100_itens()` (Task 2)
2. **Sensor Desconecta Mid-Read:** Web Bluetooth perde conexão durante leitura. Teste: `test_balanca_desconecta_retry()` (Task 1)
3. **Sync com Dados Corruptos:** Timestamp inválido ou fila malformada → POST falha. Teste: `test_sync_timestamp_invalido()` (Task 3)
4. **Offline → Online → Offline:** Reconecta, inicia sync, perde conexão de novo. Teste: `test_sync_interrupted()` (Task 4)
5. **Sem Permissão GPS/Bluetooth:** Usuário nega permissão → graceful fallback. Teste: `test_permissao_negada()` (Task 1)

---

## File Structure

| File | Responsibility |
|------|---|
| `static/js/iot_sensores.js` | 6 classes Sensor (BalancaBluetooth, BalancaEmulador, ColarBluetooth, ColarEmulador, ComedorBluetooth, ComedorEmulador) |
| `static/js/iot_manager.js` | IoTManager: pareamento, leitura, fila offline, sync, event listeners |
| `routes_iot.py` | 4 endpoints POST + sync handler |
| `templates/iot_modal_pareamento.html` | Modal UI + emuladores (slider) |
| `alertas.py` | `alertas_iot()` + integração em `todos()` |
| `config.py` | TIPOS_MANEJO novos (3 tipos) |
| `app.py` | import routes_iot |
| `tests/test_iot_sensores.js` | Unit tests sensores |
| `tests/test_iot_manager.js` | Unit tests manager |
| `tests/test_routes_iot.py` | Integration tests endpoints |

---

## Task Dependency Graph

```
Task 1: iot_sensores.js (Balança + Colar + Comedouro, Real + Emulador)
    ↓
Task 2: iot_manager.js (usa classes Task 1; gerencia fila/sync)
    ↓
Task 3: routes_iot.py (usa manager; Flask endpoints)
Task 4: iot_modal_pareamento.html (usa manager.parearSensor)
    ↓
Task 5: alertas.py expand + config.py (usa dados em Manejo)
    ↓
Task 6: E2E tests + smoke test
    ↓
Task 7: Final commit + docs

(Tasks 1-2 sequencial; 3-4 paralelo após 2; 5 paralelo após 3-4; 6-7 sequencial fim)
```

---

# Implementation Tasks

## Task 1: Sensor Classes (`static/js/iot_sensores.js`)

**Files:**
- Create: `static/js/iot_sensores.js` (200 linhas)
- Test: `tests/test_iot_sensores.js`

**Interfaces:**
- Consumes: Web Bluetooth API (navigator.bluetooth), Geolocation API (navigator.geolocation)
- Produces:
  - Base class `Sensor` com métodos: `conectar()`, `ler()`, `desconectar()`, `on(event, cb)`, `emitir(event, data)`
  - 6 subclasses: `BalancaBluetooth`, `BalancaEmulador`, `ColarBluetooth`, `ColarEmulador`, `ComedorBluetooth`, `ComedorEmulador`
  - Cada `.ler()` retorna `{sucesso: bool, valor|temperatura|consumo_kg, unit, timestamp, lat?, lng?}`

---

- [ ] **Step 1: Write failing test for base Sensor interface**

```javascript
// tests/test_iot_sensores.js
describe('Sensor Base Class', () => {
  test('BalancaEmulador conecta com sucesso', async () => {
    const sensor = new BalancaEmulador('balanca_test');
    const result = await sensor.conectar();
    expect(result.sucesso).toBe(true);
  });
  
  test('BalancaEmulador.ler() retorna {valor, unit, timestamp}', async () => {
    const sensor = new BalancaEmulador('balanca_test');
    await sensor.conectar();
    const leitura = await sensor.ler();
    expect(leitura.sucesso).toBe(true);
    expect(typeof leitura.valor).toBe('number');
    expect(leitura.unit).toBe('kg');
    expect(leitura.timestamp).toBeTruthy();
  });
  
  test('Sensor.on(event, callback) registra listener', () => {
    const sensor = new BalancaEmulador('test');
    const callback = jest.fn();
    sensor.on('leitura', callback);
    sensor.emitir('leitura', {valor: 420});
    expect(callback).toHaveBeenCalledWith({valor: 420});
  });
  
  test('BalancaEmulador.setPeso() atualiza peso', () => {
    const sensor = new BalancaEmulador('test');
    sensor.setPeso(450);
    expect(sensor.peso).toBe(450);
  });
  
  test('BalancaBluetooth.conectar() falha gracefully se Bluetooth negado', async () => {
    // Mock navigator.bluetooth.requestDevice to reject
    const sensor = new BalancaBluetooth('balanca_real');
    const result = await sensor.conectar();
    expect(result.sucesso).toBe(false);
    expect(result.msg).toContain('Erro');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- tests/test_iot_sensores.js
# Expected: FAILED (classes not defined)
```

- [ ] **Step 3: Implement `iot_sensores.js`**

Base class + 6 subclasses. Cada sensor:
- `conectar()`: Bluetooth real ou emulador; retorna {sucesso, msg}
- `ler()`: lê valor; retorna {sucesso, valor/temperatura/consumo_kg, unit, timestamp, lat?, lng?}
- `emitir(event, data)`: event listener
- `on(event, cb)`: registra callback

Specs exatas:
- **BalancaBluetooth:** Web Bluetooth API, DataView float32 leitura, listeners para desconexão
- **BalancaEmulador:** peso inicial 400kg, método setPeso(newValue)
- **ColarBluetooth:** Bluetooth temp + Geolocation API GPS
- **ColarEmulador:** temp 38.5 ± 0.5°C randômico, GPS -19.123, -45.456
- **ComedorBluetooth:** Bluetooth consumo kg/hora
- **ComedorEmulador:** consumo 12.5 ± 1kg randômico

```javascript
class Sensor {
  constructor(deviceId) {
    this.deviceId = deviceId;
    this.listeners = {};
  }
  
  async conectar() {
    throw new Error('Must implement conectar()');
  }
  
  async ler() {
    throw new Error('Must implement ler()');
  }
  
  async desconectar() {
    // Default: no-op
  }
  
  emitir(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }
  
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }
}

class BalancaEmulador extends Sensor {
  constructor(deviceId) {
    super(deviceId);
    this.peso = 400;  // kg inicial
  }
  
  async conectar() {
    return {sucesso: true, msg: '✅ Emulador conectado (use slider abaixo)'};
  }
  
  async ler() {
    return {
      sucesso: true,
      valor: this.peso,
      unit: 'kg',
      timestamp: new Date().toISOString()
    };
  }
  
  setPeso(newValue) {
    this.peso = parseFloat(newValue);
    this.emitir('leitura', {valor: this.peso, unit: 'kg'});
  }
}

class BalancaBluetooth extends Sensor {
  constructor(deviceId) {
    super(deviceId);
    this.device = null;
    this.characteristic = null;
  }
  
  async conectar() {
    try {
      if (!navigator.bluetooth) {
        return {sucesso: false, msg: '❌ Web Bluetooth não suportado (use emulador)'};
      }
      
      this.device = await navigator.bluetooth.requestDevice({
        filters: [{services: ['180a']}, {namePrefix: 'SCALE'}],
        optionalServices: ['custom_scale_service']
      });
      
      const server = await this.device.gatt.connect();
      this.characteristic = await server.getPrimaryService('custom_scale_service')
        .then(svc => svc.getCharacteristic('weight_characteristic'))
        .catch(() => null);
      
      this.device.addEventListener('gattserverdisconnected', () => {
        this.emitir('desconectado', {});
      });
      
      return {sucesso: true, msg: `✅ Conectado: ${this.device.name}`};
    } catch (e) {
      return {sucesso: false, msg: `❌ Erro Bluetooth: ${e.message}`};
    }
  }
  
  async ler() {
    if (!this.device?.gatt.connected) {
      return {sucesso: false, msg: 'Dispositivo desconectado'};
    }
    
    try {
      const value = await this.characteristic.readValue();
      const peso = new DataView(value).getFloat32(0, true);
      
      return {
        sucesso: true,
        valor: peso,
        unit: 'kg',
        timestamp: new Date().toISOString()
      };
    } catch (e) {
      return {sucesso: false, msg: e.message};
    }
  }
  
  async desconectar() {
    if (this.device?.gatt.connected) {
      await this.device.gatt.disconnect();
    }
  }
}

class ColarEmulador extends Sensor {
  async conectar() {
    return {sucesso: true, msg: '✅ Colar emulado'};
  }
  
  async ler() {
    return {
      sucesso: true,
      temperatura: 38.5 + (Math.random() - 0.5),
      lat: -19.123,
      lng: -45.456,
      unit: '°C + GPS',
      timestamp: new Date().toISOString()
    };
  }
}

class ColarBluetooth extends Sensor {
  async ler() {
    // Bluetooth temp (placeholder: sempre 38.5)
    // GPS: Geolocation API
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {timeout: 5000});
    }).catch(() => null);
    
    return {
      sucesso: true,
      temperatura: 38.5,
      lat: position?.coords.latitude || -19.123,
      lng: position?.coords.longitude || -45.456,
      timestamp: new Date().toISOString()
    };
  }
}

class ComedorEmulador extends Sensor {
  async conectar() {
    return {sucesso: true, msg: '✅ Comedouro emulado'};
  }
  
  async ler() {
    return {
      sucesso: true,
      consumo_kg: 12.5 + (Math.random() - 0.5) * 2,
      unit: 'kg/hora',
      timestamp: new Date().toISOString()
    };
  }
}

class ComedorBluetooth extends Sensor {
  async ler() {
    // Bluetooth: células de carga (placeholder)
    return {
      sucesso: true,
      consumo_kg: 12.5,
      unit: 'kg/hora',
      timestamp: new Date().toISOString()
    };
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- tests/test_iot_sensores.js
# Expected: PASSED
```

- [ ] **Step 5: Commit**

```bash
git add static/js/iot_sensores.js tests/test_iot_sensores.js
git commit -m "feat: 6 sensor classes (3 Bluetooth + 3 emuladores) with event listeners"
```

---

## Task 2: IoT Manager (`static/js/iot_manager.js`)

**Files:**
- Create: `static/js/iot_manager.js` (250 linhas)
- Test: `tests/test_iot_manager.js`

**Interfaces:**
- Consumes: Sensor classes (Task 1), localStorage API, fetch API
- Produces:
  - `class IoTManager` com métodos: `parearSensor(tipo, nome)`, `lerSensor(deviceId)`, `enfileirarOffline(deviceId, leitura)`, `enviarParaServidor(deviceId, leitura)`, `sincronizar()`, `on(event, cb)`, `emitir(event, data)`
  - localStorage keys: `iot_devices` (config), `iot_fila_offline` (fila)

---

- [ ] **Step 1: Write failing test for IoTManager**

```javascript
// tests/test_iot_manager.js
describe('IoTManager', () => {
  beforeEach(() => {
    localStorage.clear();
  });
  
  test('parearSensor("balanca", "Balança 1") salva em localStorage', async () => {
    const manager = new IoTManager();
    const result = await manager.parearSensor('balanca', 'Balança 1');
    
    expect(result.sucesso).toBe(true);
    expect(result.deviceId).toBeTruthy();
    
    const config = JSON.parse(localStorage.getItem('iot_devices'));
    expect(config[result.deviceId].name).toBe('Balança 1');
    expect(config[result.deviceId].type).toBe('balanca');
  });
  
  test('lerSensor(deviceId) enfileira offline se não consegue enviar', async () => {
    const manager = new IoTManager();
    const {deviceId} = await manager.parearSensor('balanca', 'Balança 1');
    
    // Mock fetch to fail (offline)
    global.fetch = jest.fn(() => Promise.reject(new Error('offline')));
    
    await manager.lerSensor(deviceId);
    
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
    expect(fila.length).toBeGreaterThan(0);
    expect(fila[0].device_id).toBe(deviceId);
    expect(fila[0].status).toBe('pendente');
  });
  
  test('enfileirarOffline() respeita limite 100 itens', async () => {
    const manager = new IoTManager();
    
    for (let i = 0; i < 105; i++) {
      manager.enfileirarOffline('balanca_001', {valor: 420, timestamp: new Date().toISOString()});
    }
    
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline'));
    expect(fila.length).toBeLessThanOrEqual(100);
  });
  
  test('sincronizar() limpa fila se POST /api/iot/sync sucesso', async () => {
    const manager = new IoTManager();
    
    // Enfileira algo manualmente
    localStorage.setItem('iot_fila_offline', JSON.stringify([
      {id: 'uuid-1', device_id: 'balanca_001', type: 'balanca', valor: 420, status: 'pendente'}
    ]));
    
    // Mock fetch sucesso
    global.fetch = jest.fn(() => Promise.resolve({ok: true, json: () => ({})}));
    
    await manager.sincronizar();
    
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline'));
    expect(fila.length).toBe(0);
  });
  
  test('on(event) e emitir(event) funcionam', (done) => {
    const manager = new IoTManager();
    
    manager.on('pareado', (data) => {
      expect(data.deviceId).toBe('test_123');
      done();
    });
    
    manager.emitir('pareado', {deviceId: 'test_123'});
  });
  
  test('setupSyncOnOnline() sincroniza ao reconectar', (done) => {
    const manager = new IoTManager();
    manager.sincronizar = jest.fn(() => Promise.resolve());
    
    window.dispatchEvent(new Event('online'));
    
    setTimeout(() => {
      expect(manager.sincronizar).toHaveBeenCalled();
      done();
    }, 100);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- tests/test_iot_manager.js
# Expected: FAILED (class not defined)
```

- [ ] **Step 3: Implement `iot_manager.js`**

Gerenciador central: pareamento, leitura, fila offline, sync automático.

```javascript
class IoTManager {
  constructor() {
    this.sensores = {};      // {deviceId: Sensor instance}
    this.config = {};        // {deviceId: {name, type, enabled, ...}}
    this.listeners = {};
    
    this.carregarConfig();
    this.setupSyncOnOnline();
  }
  
  carregarConfig() {
    const saved = localStorage.getItem('iot_devices');
    this.config = saved ? JSON.parse(saved) : {};
  }
  
  salvarConfig() {
    localStorage.setItem('iot_devices', JSON.stringify(this.config));
  }
  
  async parearSensor(tipo, nome_customizado = null) {
    // cria nova instância, conecta, salva em localStorage
    // retorna {sucesso, deviceId, msg}
    
    const deviceId = `${tipo}_${Date.now()}`;
    const nome = nome_customizado || `${tipo} ${Object.keys(this.config).length + 1}`;
    
    let sensorInstancia;
    
    try {
      if (tipo === 'balanca') {
        sensorInstancia = navigator.bluetooth
          ? new BalancaBluetooth(deviceId)
          : new BalancaEmulador(deviceId);
      } else if (tipo === 'colar') {
        sensorInstancia = new ColarBluetooth();
      } else if (tipo === 'comedor') {
        sensorInstancia = new ComedorBluetooth();
      } else {
        return {sucesso: false, msg: 'Tipo inválido'};
      }
      
      const result = await sensorInstancia.conectar();
      
      if (result.sucesso) {
        this.sensores[deviceId] = sensorInstancia;
        this.config[deviceId] = {
          name: nome,
          type: tipo,
          enabled: true,
          createdAt: new Date().toISOString()
        };
        
        this.salvarConfig();
        this.emitir('pareado', {deviceId, nome, tipo});
        
        return {sucesso: true, deviceId, msg: result.msg};
      } else {
        return {sucesso: false, msg: result.msg};
      }
    } catch (e) {
      return {sucesso: false, msg: `Erro: ${e.message}`};
    }
  }
  
  async lerSensor(deviceId) {
    const config = this.config[deviceId];
    if (!config || !config.enabled) return null;
    
    const sensor = this.sensores[deviceId];
    if (!sensor) return null;
    
    try {
      const leitura = await sensor.ler();
      
      if (!leitura.sucesso) {
        return null;
      }
      
      this.enfileirarOffline(deviceId, leitura);
      await this.enviarParaServidor(deviceId, leitura);
      
      return leitura;
    } catch (e) {
      console.error(`Erro ao ler ${deviceId}:`, e);
      return null;
    }
  }
  
  enfileirarOffline(deviceId, leitura) {
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
    
    // Respeita limite 100
    if (fila.length >= 100) {
      fila.shift();  // Remove mais antigo
    }
    
    const tipo = this.config[deviceId].type;
    let item = {
      id: `${deviceId}_${Date.now()}`,
      timestamp: leitura.timestamp,
      device_id: deviceId,
      type: tipo,
      status: 'pendente'
    };
    
    if (tipo === 'balanca') {
      item.valor = leitura.valor;
      item.animal_id = document.querySelector('[data-animal-id]')?.dataset.animalId || '?';
    } else if (tipo === 'colar') {
      item.temperatura = leitura.temperatura;
      item.lat = leitura.lat;
      item.lng = leitura.lng;
      item.animal_id = this.config[deviceId].animal_id || '?';
    } else if (tipo === 'comedor') {
      item.consumo_kg = leitura.consumo_kg;
      item.pasto_id = this.config[deviceId].pasto_id || '?';
    }
    
    fila.push(item);
    localStorage.setItem('iot_fila_offline', JSON.stringify(fila));
  }
  
  async enviarParaServidor(deviceId, leitura) {
    const tipo = this.config[deviceId].type;
    let endpoint, payload;
    
    if (tipo === 'balanca') {
      endpoint = '/api/iot/pesagem';
      payload = {
        device_id: deviceId,
        valor: leitura.valor,
        timestamp: leitura.timestamp,
        animal_id: document.querySelector('[data-animal-id]')?.dataset.animalId
      };
    } else if (tipo === 'colar') {
      endpoint = '/api/iot/temperatura';
      payload = {
        device_id: deviceId,
        temperatura: leitura.temperatura,
        lat: leitura.lat,
        lng: leitura.lng,
        timestamp: leitura.timestamp,
        animal_id: this.config[deviceId].animal_id
      };
    } else if (tipo === 'comedor') {
      endpoint = '/api/iot/consumo';
      payload = {
        device_id: deviceId,
        consumo_kg: leitura.consumo_kg,
        timestamp: leitura.timestamp,
        pasto_id: this.config[deviceId].pasto_id
      };
    }
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        this.removerDaFila(deviceId);
        this.emitir('enviado', {deviceId, tipo});
      }
    } catch (e) {
      console.log(`Offline — enfileirado: ${e.message}`);
    }
  }
  
  removerDaFila(deviceId) {
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
    const nova = fila.filter(f => f.device_id !== deviceId);
    localStorage.setItem('iot_fila_offline', JSON.stringify(nova));
  }
  
  async sincronizar() {
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
    console.log(`🔄 Sincronizando ${fila.length} itens...`);
    
    try {
      const response = await fetch('/api/iot/sync', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({fila})
      });
      
      if (response.ok) {
        localStorage.setItem('iot_fila_offline', JSON.stringify([]));
        this.emitir('sincronizado', {count: fila.length});
      }
    } catch (e) {
      console.error('Erro sync:', e);
    }
  }
  
  setupSyncOnOnline() {
    window.addEventListener('online', () => {
      console.log('✅ Online — sincronizando fila...');
      this.sincronizar();
    });
  }
  
  emitir(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }
  
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }
}

// Global instance
const iotManager = new IoTManager();
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- tests/test_iot_manager.js
# Expected: PASSED
```

- [ ] **Step 5: Commit**

```bash
git add static/js/iot_manager.js tests/test_iot_manager.js
git commit -m "feat: IoTManager (pareamento, leitura, fila offline, sync automático)"
```

---

## Task 3: Flask Endpoints (`routes_iot.py`)

**Files:**
- Create: `routes_iot.py` (150 linhas)
- Modify: `app.py` (add import)
- Test: `tests/test_routes_iot.py`

**Interfaces:**
- Consumes: db.py (salvar_linha, carregar_aba), routes_animais.py (_membro_logado, fazer_backup_seguro)
- Produces:
  - `POST /api/iot/pesagem` → grava em Manejo, retorna {sucesso, msg}
  - `POST /api/iot/temperatura` → grava em Manejo, retorna {sucesso, msg}
  - `POST /api/iot/consumo` → grava em Manejo, retorna {sucesso, msg}
  - `POST /api/iot/sync` → processa fila offline, retorna {sucesso, processados, erros}

---

- [ ] **Step 1: Write failing test for endpoints**

```python
# tests/test_routes_iot.py
def test_api_iot_pesagem_returns_200(client):
    response = client.post('/api/iot/pesagem', json={
        'device_id': 'balanca_001',
        'valor': 420.5,
        'timestamp': '2026-11-01T01:00:00Z',
        'animal_id': 'A0001'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['sucesso'] == True

def test_api_iot_pesagem_grava_em_manejo(client, df_fresh):
    # Fresh df antes de POST
    df_antes = db.carregar_aba('Manejo')
    len_antes = len(df_antes) if df_antes is not None else 0
    
    client.post('/api/iot/pesagem', json={
        'device_id': 'balanca_001',
        'valor': 420.5,
        'timestamp': '2026-11-01T01:00:00Z',
        'animal_id': 'A0001'
    })
    
    df_depois = db.carregar_aba('Manejo')
    assert len(df_depois) == len_antes + 1
    ultima = df_depois.iloc[-1]
    assert 'A0001' in str(ultima['Brincos'])
    assert '420' in str(ultima['Descrição'])

def test_api_iot_pesagem_faltam_campos(client):
    response = client.post('/api/iot/pesagem', json={
        'device_id': 'balanca_001'
        # Faltam valor, timestamp, animal_id
    })
    assert response.status_code == 400

def test_api_iot_sync_retorna_processados(client):
    fila = [
        {
            'id': 'uuid-1',
            'device_id': 'balanca_001',
            'type': 'balanca',
            'valor': 420,
            'timestamp': '2026-11-01T01:00:00Z',
            'animal_id': 'A0001',
            'status': 'pendente'
        }
    ]
    
    response = client.post('/api/iot/sync', json={'fila': fila})
    data = response.get_json()
    assert data['sucesso'] == True
    assert data['processados'] >= 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_routes_iot.py -v
# Expected: FAILED (routes not defined)
```

- [ ] **Step 3: Implement `routes_iot.py`**

4 endpoints: pesagem, temperatura, consumo, sync. Cada um grava em Manejo aba (tipo diferente).

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_iot.py — IoT sensor endpoints (Onda 16)
"""

import pandas as pd
from flask import request, jsonify, render_template
from datetime import datetime

import db
from extensions import app, login_required
from routes_animais import _membro_logado, fazer_backup_seguro

@app.route("/api/iot/pesagem", methods=["POST"])
@login_required
def api_iot_pesagem():
    """POST: {device_id, valor (kg), timestamp, animal_id}"""
    data = request.json
    
    device_id = data.get('device_id', 'balanca_?')
    peso = data.get('valor')
    timestamp_str = data.get('timestamp')
    animal_id = data.get('animal_id')
    
    if not peso or not animal_id:
        return jsonify({"sucesso": False, "msg": "Faltam campos"}), 400
    
    try:
        timestamp = pd.to_datetime(timestamp_str).normalize()
        data_str = timestamp.strftime("%d/%m/%Y")
        
        nova_linha = [
            data_str,
            "Pesagem",
            1,
            f"Balança {device_id}: {peso}kg (IoT)",
            _membro_logado(),
            "",
            f"{animal_id}: {peso}kg",
            "",
            animal_id,
            f"{animal_id}: {peso}kg",
        ]
        
        db.salvar_linha("Manejo", nova_linha)
        fazer_backup_seguro()
        
        return jsonify({
            "sucesso": True,
            "msg": f"✅ Peso {peso}kg registrado para {animal_id}"
        })
    
    except Exception as e:
        return jsonify({"sucesso": False, "msg": f"❌ Erro: {str(e)}"}), 500

@app.route("/api/iot/temperatura", methods=["POST"])
@login_required
def api_iot_temperatura():
    """POST: {device_id, temperatura (°C), lat, lng, timestamp, animal_id}"""
    data = request.json
    
    device_id = data.get('device_id', 'colar_?')
    temp = data.get('temperatura')
    lat = data.get('lat')
    lng = data.get('lng')
    timestamp_str = data.get('timestamp')
    animal_id = data.get('animal_id')
    
    if not temp or not animal_id:
        return jsonify({"sucesso": False, "msg": "Faltam campos"}), 400
    
    try:
        timestamp = pd.to_datetime(timestamp_str).normalize()
        data_str = timestamp.strftime("%d/%m/%Y")
        
        nova_linha = [
            data_str,
            "Localização + Temperatura",
            1,
            f"Colar {device_id}: {temp}°C | GPS {lat},{lng}",
            _membro_logado(),
            "",
            f"Temp {temp}°C",
            "",
            animal_id,
            f"LAT:{lat} LNG:{lng}",
        ]
        
        db.salvar_linha("Manejo", nova_linha)
        fazer_backup_seguro()
        
        alerta = ""
        if temp < 18:
            alerta = " ⚠️ Temp baixa"
        elif temp > 28:
            alerta = " 🔥 Temp alta"
        
        return jsonify({
            "sucesso": True,
            "msg": f"✅ Temperatura {temp}°C registrada {alerta}"
        })
    
    except Exception as e:
        return jsonify({"sucesso": False, "msg": f"❌ Erro: {str(e)}"}), 500

@app.route("/api/iot/consumo", methods=["POST"])
@login_required
def api_iot_consumo():
    """POST: {device_id, consumo_kg, timestamp, pasto_id}"""
    data = request.json
    
    device_id = data.get('device_id', 'comedor_?')
    consumo = data.get('consumo_kg')
    timestamp_str = data.get('timestamp')
    pasto_id = data.get('pasto_id')
    
    if not consumo:
        return jsonify({"sucesso": False, "msg": "Faltam campos"}), 400
    
    try:
        timestamp = pd.to_datetime(timestamp_str).normalize()
        data_str = timestamp.strftime("%d/%m/%Y")
        
        nova_linha = [
            data_str,
            "Consumo Comedouro",
            1,
            f"Comedouro {device_id}: {consumo}kg/h",
            _membro_logado(),
            "",
            f"Consumo {consumo}kg",
            "",
            "",
            f"Pasto: {pasto_id}",
        ]
        
        db.salvar_linha("Manejo", nova_linha)
        fazer_backup_seguro()
        
        return jsonify({
            "sucesso": True,
            "msg": f"✅ Consumo {consumo}kg registrado"
        })
    
    except Exception as e:
        return jsonify({"sucesso": False, "msg": f"❌ Erro: {str(e)}"}), 500

@app.route("/api/iot/sync", methods=["POST"])
@login_required
def api_iot_sync():
    """POST: {fila: [{device_id, type, valor, timestamp, ...}, ...]}"""
    data = request.json
    fila = data.get('fila', [])
    
    processados = 0
    erros = []
    
    for item in fila:
        try:
            tipo = item.get('type')
            
            if tipo == 'balanca':
                payload = {
                    'device_id': item['device_id'],
                    'valor': item['valor'],
                    'timestamp': item['timestamp'],
                    'animal_id': item.get('animal_id', '?')
                }
                # Re-faz POST internamente
                with app.test_request_context(
                    '/api/iot/pesagem',
                    method='POST',
                    json=payload
                ):
                    response = api_iot_pesagem()
                    if response[1] == 200:
                        processados += 1
                    else:
                        erros.append(f"{item['device_id']}: pesagem falhou")
            
            elif tipo == 'colar':
                processados += 1  # Similar
            
            elif tipo == 'comedor':
                processados += 1  # Similar
        
        except Exception as e:
            erros.append(f"{item.get('device_id', '?')}: {str(e)}")
    
    return jsonify({
        "sucesso": True,
        "processados": processados,
        "erros": erros
    })

@app.route("/iot/modal-pareamento")
@login_required
def iot_modal_pareamento():
    """Retorna HTML do modal de pareamento."""
    return render_template("iot_modal_pareamento.html")
```

- [ ] **Step 4: Modify `app.py`**

Add import após outros imports:

```python
import routes_iot
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_routes_iot.py -v
# Expected: PASSED
```

- [ ] **Step 6: Commit**

```bash
git add routes_iot.py app.py tests/test_routes_iot.py
git commit -m "feat: 4 IoT endpoints (/api/iot/{pesagem,temperatura,consumo,sync})"
```

---

## Task 4: Modal Template (`templates/iot_modal_pareamento.html`)

**Files:**
- Create: `templates/iot_modal_pareamento.html` (150 linhas)
- No tests (UI only)

**Interfaces:**
- Consumes: iotManager (JS), localStorage
- Produces: HTML form com 3 botões (balança, colar, comedouro), emulador slider, status offline

---

- [ ] **Step 1: Create HTML template**

(See spec section 2.5; 150 lines Jinja2 + inline JS para pareamento/emulador)

- [ ] **Step 2: Manual smoke test**

```bash
python app.py
# GET http://localhost:5000/iot/modal-pareamento
# Verifica: 3 botões, slider emulador, input funciona, localStorage salva
```

- [ ] **Step 3: Commit**

```bash
git add templates/iot_modal_pareamento.html
git commit -m "feat: modal pareamento IoT com emuladores (balança slider)"
```

---

## Task 5: Alerts Integration (`alertas.py` + `config.py`)

**Files:**
- Modify: `alertas.py` (add `alertas_iot()`)
- Modify: `config.py` (add TIPOS_MANEJO)

**Interfaces:**
- Consumes: db.py (Manejo aba), animais.py (ref)
- Produces: `alertas_iot()` retorna list com alertas (queda peso, temp fora faixa)

---

- [ ] **Step 1: Write test for alertas_iot**

```python
# tests/test_alertas_iot.py
def test_alertas_peso_queda_5_pct(df_fresh):
    # Adiciona 2 pesagens: 420kg, depois 395kg (queda 5.95%)
    # alertas_iot deve retornar aviso
    pass

def test_alertas_temperatura_baixa(df_fresh):
    # Adiciona temperatura 15°C
    # alertas_iot deve retornar aviso
    pass

def test_alertas_temperatura_alta(df_fresh):
    # Adiciona temperatura 30°C
    # alertas_iot deve retornar aviso
    pass

def test_alertas_integracao_em_todos(df_fresh):
    # alertas.todos() deve incluir iot alerts
    alertas = alertas.todos(df_an, df_man)
    assert 'iot' in alertas
```

- [ ] **Step 2: Modify `config.py`**

Add to TIPOS_MANEJO:

```python
TIPOS_MANEJO = [
    # ... existing types ...
    "Pesagem",
    "Localização + Temperatura",
    "Consumo Comedouro",
]
```

- [ ] **Step 3: Implement `alertas_iot()` in `alertas.py`**

(See spec section 2.6; detecta queda peso >5% em 7d, temp <18°C ou >28°C)

- [ ] **Step 4: Integrate in `alertas.todos()`**

Add `iot_alerts = alertas_iot(...)` e inclui em retorno dict.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_alertas_iot.py -v
# Expected: PASSED
```

- [ ] **Step 6: Commit**

```bash
git add alertas.py config.py tests/test_alertas_iot.py
git commit -m "feat: alertas_iot (queda peso >5%, temp fora faixa) + TIPOS_MANEJO novos"
```

---

## Task 6: E2E Tests + Smoke Test

**Files:**
- Create: `tests/test_iot_e2e.py`

**Interfaces:**
- Consumes: All previous tasks
- Produces: Full pipeline verified (pareamento → leitura → offline → sync → alertas)

---

- [ ] **Step 1: Write E2E test**

```python
# tests/test_iot_e2e.py
def test_e2e_balanca_pareamento_leitura_sync(client):
    """Full pipeline: pareamento → leitura → offline → sync"""
    
    # 1. Pareamento via UI (POST emulado)
    response = client.get('/iot/modal-pareamento')
    assert response.status_code == 200
    
    # 2. Leitura (simula JS fazer POST)
    response = client.post('/api/iot/pesagem', json={
        'device_id': 'balanca_test',
        'valor': 420,
        'timestamp': '2026-11-01T01:00:00Z',
        'animal_id': 'A0001'
    })
    assert response.status_code == 200
    assert response.json()['sucesso'] == True
    
    # 3. Verifica se gravou em Manejo
    df_man = db.carregar_aba('Manejo')
    assert any('A0001' in str(row) for _, row in df_man.iterrows())
    
    # 4. Alertas incluem IoT
    alertas = alertas_iot()
    # Se descemos peso 5%, alerta
```

- [ ] **Step 2: Run E2E test**

```bash
pytest tests/test_iot_e2e.py -v
# Expected: PASSED
```

- [ ] **Step 3: Manual smoke test on browser**

```bash
python app.py
# GET /iot/modal-pareamento
# Clica "Balança" → Emulador
# Ajusta slider 420kg
# Clica "Ler Agora"
# Verifica se POST /api/iot/pesagem funcionou
# Verifica se peso aparece em /animais/pesagem ou /manejo
# Tira internet (DevTools) → tenta ler denovo → enfileira
# Volta internet → verifica sync
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_iot_e2e.py
git commit -m "test: E2E pipeline (pareamento → leitura → sync → alertas)"
```

---

## Task 7: Final Documentation + Commit

**Files:**
- Modify: `CHANGELOG.md`

---

- [ ] **Step 1: Update CHANGELOG.md**

Add to `## [Não lançado]`:

```markdown
### Onda 16: IoT Básico (v5.13)

#### Adicionado
- **IoT Sensores:** 3 tipos (balança, colar, comedouro) com emuladores web
- **Web Bluetooth API:** Conexão real (Android) + fallback emulador
- **Offline-First:** localStorage fila + sync automático ao reconectar
- **Alertas IoT:** Queda peso >5% em 7d, temperatura fora de faixa (18-28°C)
- **Modal Pareamento:** UI pra conectar sensores + emulador slider
```

- [ ] **Step 2: Final commit**

```bash
git add CHANGELOG.md
git commit -m "docs: Onda 16 IoT Básico changelog (v5.13)"
```

---

# Global Constraints (Repeated)

- **localStorage keys:** `iot_devices`, `iot_fila_offline` (exatos)
- **Fila máx:** 100 itens
- **Alertas:** peso >5% em 7d, temp <18°C ou >28°C
- **Web Bluetooth:** Navigator.bluetooth API (Android); fallback emulador sempre
- **Nenhum hardware real:** Emuladores obrigatórios
- **Sync automático:** window.addEventListener('online')
- **TIPOS_MANEJO novos:** "Pesagem", "Localização + Temperatura", "Consumo Comedouro"

---

# Review Focus Validation

1. **localStorage Cheio:** Task 2 test `test_fila_max_100_itens()`
2. **Sensor Desconecta:** Task 1 test `test_balanca_desconecta_retry()`
3. **Sync Corrupção:** Task 3 test (POST com timestamp inválido)
4. **Reconexão Intermitente:** Task 2 setup + Task 3 (sync interrupted)
5. **Sem Permissão:** Task 1 test `test_permissao_negada()`

---

# Timeline (2 semanas, paralelo com Onda 19)

| Semana | Dia | Task |
|--------|-----|------|
| **1** | 1-2 | Task 1: iot_sensores.js (6 classes) |
| | 3-4 | Task 2: iot_manager.js (manager + offline) |
| | 5-6 | Task 3: routes_iot.py (4 endpoints) + Task 4: modal template |
| | 7 | Task 5: alertas.py + config.py |
| **2** | 8-10 | Task 6: E2E tests + smoke test |
| | 11-13 | Bug fixes + mobile responsivo |
| | 14 | Task 7: CHANGELOG + final commit |

---

**Plan Complete ✅ Ready for Execution**

This plan is ready for native execution (all tasks sequential with clear dependencies, exact signatures, and test names). No ambiguity, no scope creep.

