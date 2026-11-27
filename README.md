# Sítio Santo Antônio — Sistema de Gestão Pecuária

Sistema web completo para gerenciamento de pecuária (corte e leite), controle de rebanho, manejo sanitário, financeiro, pastagens, previsão do tempo integrada e inteligência artificial preditiva (risco de morte, cio e consanguinidade).

---

## 🚀 Funcionalidades Principais

- **Painel Geral (Dashboard):** Visão geral do rebanho, alertas de IA, clima atual e previsões.
- **Controle de Animais:** Cadastro completo de bovinos (identificação, raça, peso, categoria, histórico genealógico).
- **Manejo e Reprodução:** Registro de coberturas, cios, partos, vacinas e tratamentos sanitários.
- **Saúde do Leite / Mastite:** Monitoramento de saúde do úbere e qualidade do leite.
- **Mapeamento de Pastos:** Gestão de piquetes e lotação de animais.
- **Previsão do Tempo:** Integração com Open-Meteo com suporte a geolocalização e alertas automáticos para o conforto animal.
- **IA Preditiva:** Modelos de Machine Learning (RandomForest / GradientBoosting) para prever riscos sanitários, cio e ganho de peso, com pipeline de treinamento automatizado.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python / Flask
- **Banco de Dados / Armazenamento:** SQLite / Arquivos Excel (`.xlsx`)
- **Machine Learning:** Scikit-learn, NumPy, Pandas
- **Frontend:** HTML5, CSS3, JavaScript, Tailwind/Bootstrap, FontAwesome

---

## 📦 Instalação e Execução Local

1. Clone o repositório:
   ```bash
   git clone https://github.com/deyvidgt/gado-sitio.git
   cd gado-sitio
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/macOS:
   source venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Treine os modelos de IA preditiva (opcional/inicialização):
   ```bash
   python scripts/train_ia_modelos.py
   ```

5. Inicie a aplicação Flask:
   ```bash
   python app.py
   ```

6. Acesse no navegador: `http://localhost:5000`

---

## 📄 Licença

Projeto desenvolvido para uso interno no Sítio Santo Antônio.
