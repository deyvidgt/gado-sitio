/**
 * static/js/iot_manager.js — Gerencia sensores, fila offline, sync automático
 */

class IoTManager {
  constructor() {
    this.sensores = {};
    this.fila_offline = [];
    this.max_fila = 100;
    this.sincronizando = false;
    this.carregarConfiguracao();
  }

  carregarConfiguracao() {
    try {
      const cfg = JSON.parse(localStorage.getItem('iot_devices') || '{}');
      this.sensores = cfg;
    } catch (e) {
      console.error('Erro ao carregar config IoT:', e);
    }
  }

  salvarConfiguracao() {
    localStorage.setItem('iot_devices', JSON.stringify(this.sensores));
  }

  carregarFila() {
    try {
      this.fila_offline = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
    } catch (e) {
      console.error('Erro ao carregar fila:', e);
      this.fila_offline = [];
    }
  }

  salvarFila() {
    if (this.fila_offline.length > this.max_fila) {
      console.warn('Fila excedeu 100 itens, limpando...');
      this.fila_offline = this.fila_offline.slice(-this.max_fila);
    }
    localStorage.setItem('iot_fila_offline', JSON.stringify(this.fila_offline));
  }

  adicionarFila(tipo, dados) {
    if (this.fila_offline.length >= this.max_fila) {
      console.warn('Fila cheia, descartando leitura mais antiga');
      this.fila_offline.shift();
    }
    this.fila_offline.push({
      tipo,
      dados,
      timestamp: new Date().toISOString(),
      id_envio: Date.now() + Math.random()
    });
    this.salvarFila();
  }

  async lerSensor(tipo, id_sensor) {
    const cfg_key = `${tipo}_${id_sensor}`;
    const cfg = this.sensores[cfg_key] || {};

    // Escolhe real ou emulador
    let sensor;
    if (cfg.tipo_conexao === 'emulador') {
      if (tipo === 'balanca') sensor = new BalancaEmulador(id_sensor);
      else if (tipo === 'colar') sensor = new ColarEmulador(id_sensor);
      else if (tipo === 'comedouro') sensor = new ComedoroEmulador(id_sensor);
    } else {
      if (tipo === 'balanca') sensor = new BalancaBluetooth(id_sensor);
      else if (tipo === 'colar') sensor = new ColarBluetooth(id_sensor);
      else if (tipo === 'comedouro') sensor = new ComedoroBluetooth(id_sensor);
    }

    if (!sensor) return {sucesso: false, msg: 'Sensor desconhecido'};

    // Conecta e lê
    const conn = await sensor.conectar();
    if (!conn.sucesso) {
      this.adicionarFila(tipo, {msg: conn.msg});
      return conn;
    }

    const leitura = await sensor.ler();
    await sensor.desconectar();

    if (leitura.sucesso) {
      this.adicionarFila(tipo, leitura);
      return leitura;
    }
    return leitura;
  }

  async sincronizar() {
    if (this.sincronizando || this.fila_offline.length === 0) return;

    this.sincronizando = true;
    const fila_backup = [...this.fila_offline];

    try {
      const response = await fetch('/api/iot/sync', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({itens: this.fila_offline})
      });

      if (response.ok) {
        this.fila_offline = [];
        this.salvarFila();
        console.log('✅ Sync OK');
      } else {
        console.warn('Sync falhou, mantendo fila');
        this.fila_offline = fila_backup;
      }
    } catch (e) {
      console.error('Erro sync:', e);
      this.fila_offline = fila_backup;
    } finally {
      this.sincronizando = false;
    }
  }

  iniciarSyncAutomatico(intervalo_ms = 30000) {
    setInterval(() => this.sincronizar(), intervalo_ms);
  }
}

// Exporta para uso global
window.iotManager = new IoTManager();
