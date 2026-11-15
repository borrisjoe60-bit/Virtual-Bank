(() => {
  const root = document.getElementById("vsc-wallet-panel");
  if (!root) return;
  const API = (window.API_BASE_URL || "").replace(/\/$/, "");
  const CHAIN_HEX = "0x668ca";
  const RPC_URLS = ["https://rpc.vscblockchain.org", "https://420042.rpc.thirdweb.com"];
  const EXPLORER = "https://explorer.vscblockchain.org";
  let connectedAddress = "";
  const statusNode = document.getElementById("vsc-network-status");
  const feedback = document.getElementById("vsc-feedback");
  const list = document.getElementById("vsc-wallet-list");
  const addressInput = document.getElementById("vsc-wallet-address");
  const registerButton = document.getElementById("vsc-register-wallet");
  const connectButton = document.createElement("button");
  connectButton.type = "button";
  connectButton.className = "btn btn-outline-primary btn-sm ms-2";
  connectButton.textContent = "Connect MetaMask";
  statusNode.insertAdjacentElement("afterend", connectButton);

  const csrf = () => {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  };
  async function api(path, options = {}) {
    const headers = { Accept: "application/json" };
    if (options.body) headers["Content-Type"] = "application/json";
    if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrf();
    const response = await fetch(API + path, { credentials: "include", ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || ("Request failed (" + response.status + ")"));
    return data;
  }
  function element(tag, className, value) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (value !== undefined) item.textContent = value;
    return item;
  }
  function toWeiHex(value) {
    if (!/^\d+(\.\d{1,18})?$/.test(value) || Number(value) <= 0) throw new Error("Enter a valid VSG amount with up to 18 decimal places.");
    const parts = value.split(".");
    const whole = BigInt(parts[0]);
    const fraction = BigInt((parts[1] || "").padEnd(18, "0") || "0");
    return "0x" + (whole * (10n ** 18n) + fraction).toString(16);
  }
  async function ensureVscNetwork() {
    const provider = window.ethereum;
    try {
      await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: CHAIN_HEX }] });
    } catch (error) {
      if (error.code !== 4902) throw error;
      await provider.request({
        method: "wallet_addEthereumChain",
        params: [{
          chainId: CHAIN_HEX,
          chainName: "Vector Smart Chain",
          nativeCurrency: { name: "Vector Smart Gas", symbol: "VSG", decimals: 18 },
          rpcUrls: RPC_URLS,
          blockExplorerUrls: [EXPLORER]
        }]
      });
      await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: CHAIN_HEX }] });
    }
    const active = await provider.request({ method: "eth_chainId" });
    if (active.toLowerCase() !== CHAIN_HEX) throw new Error("Please switch MetaMask to Vector Smart Chain.");
  }
  async function registerAddress(address) {
    await api("/vsc/wallets/", { method: "POST", body: JSON.stringify({ address, label: "MetaMask VSG wallet" }) });
    addressInput.value = address;
  }
  async function connectWallet() {
    if (!window.ethereum) throw new Error("MetaMask or another injected EVM wallet is required. Open this dashboard in a wallet-enabled browser.");
    await ensureVscNetwork();
    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    if (!accounts || !accounts.length) throw new Error("No wallet account was selected.");
    connectedAddress = accounts[0];
    await registerAddress(connectedAddress);
    connectButton.textContent = connectedAddress.slice(0, 6) + "…" + connectedAddress.slice(-4);
    feedback.textContent = "Wallet connected and registered on Vector Smart Chain.";
    await loadWallets();
  }
  async function loadNetwork() {
    try {
      const network = await api("/vsc/network/");
      statusNode.textContent = network.rpc_status === "online" ? "VSC online · block " + network.latest_block : "VSC RPC unavailable";
      statusNode.className = "badge " + (network.rpc_status === "online" ? "text-bg-success" : "text-bg-warning");
    } catch (error) {
      statusNode.textContent = "VSC API unavailable";
      statusNode.className = "badge text-bg-danger";
    }
  }
  async function loadWallets() {
    try {
      const wallets = await api("/vsc/wallets/");
      list.replaceChildren();
      if (!wallets.length) {
        list.append(element("p", "text-muted", "No VSG wallet registered. Connect MetaMask to get started."));
        return;
      }
      for (const wallet of wallets) {
        const card = element("div", "border rounded-3 p-3 mt-3");
        const heading = element("div", "d-flex justify-content-between flex-wrap gap-2");
        heading.append(element("strong", "", wallet.label || "VSG wallet"));
        const balance = element("span", "fw-semibold", "Balance: loading…");
        heading.append(balance);
        const address = element("code", "d-block text-break small mt-2", wallet.address);
        const actions = element("div", "d-flex flex-wrap gap-2 mt-3");
        const refresh = element("button", "btn btn-sm btn-outline-primary", "Refresh balance");
        const deposit = element("button", "btn btn-sm btn-outline-secondary", "Deposit address");
        const history = element("button", "btn btn-sm btn-outline-secondary", "Transaction history");
        const explorer = element("a", "btn btn-sm btn-outline-secondary", "Explorer");
        explorer.href = wallet.explorer_url;
        explorer.target = "_blank";
        explorer.rel = "noopener noreferrer";
        [refresh, deposit, history].forEach(button => button.type = "button");
        const detail = element("div", "small mt-3");
        refresh.addEventListener("click", async () => {
          try {
            const result = await api("/vsc/wallets/" + wallet.id + "/balance/");
            balance.textContent = result.balance_vsg + " VSG";
          } catch (error) { balance.textContent = error.message; }
        });
        deposit.addEventListener("click", async () => {
          try {
            const result = await api("/vsc/wallets/" + wallet.id + "/deposit/");
            detail.textContent = result.instructions + " Deposit address: " + result.deposit_address;
          } catch (error) { detail.textContent = error.message; }
        });
        history.addEventListener("click", async () => {
          try {
            const result = await api("/vsc/wallets/" + wallet.id + "/history/");
            detail.replaceChildren();
            if (!result.items.length) detail.textContent = "No native VSG transactions found yet.";
            for (const tx of result.items) {
              const row = element("div", "border-top py-2");
              row.append(element("div", "fw-semibold", tx.direction + " · " + tx.amount_vsg + " VSG · " + tx.status));
              const link = element("a", "small", tx.tx_hash);
              link.href = tx.explorer_url;
              link.target = "_blank";
              link.rel = "noopener noreferrer";
              row.append(link);
              detail.append(row);
            }
          } catch (error) { detail.textContent = error.message; }
        });

        const sendTitle = element("h3", "h6 mt-4", "Send VSG");
        const recipient = element("input", "form-control form-control-sm mt-2");
        recipient.placeholder = "Recipient 0x wallet address";
        recipient.autocomplete = "off";
        const amount = element("input", "form-control form-control-sm mt-2");
        amount.type = "number";
        amount.min = "0.000000000000000001";
        amount.step = "0.000000000000000001";
        amount.placeholder = "Amount in VSG";
        const send = element("button", "btn btn-sm btn-warning mt-2", "Send with MetaMask");
        send.type = "button";
        if (!connectedAddress || connectedAddress.toLowerCase() !== wallet.address.toLowerCase()) send.disabled = true;
        send.title = send.disabled ? "Connect the matching wallet first." : "Review and approve this transfer in MetaMask.";
        send.addEventListener("click", async () => {
          try {
            if (!window.ethereum) throw new Error("Open this dashboard in a wallet-enabled browser.");
            if (connectedAddress.toLowerCase() !== wallet.address.toLowerCase()) throw new Error("Connect the wallet that owns this address.");
            if (!/^0x[a-fA-F0-9]{40}$/.test(recipient.value.trim())) throw new Error("Enter a valid recipient address.");
            const value = toWeiHex(amount.value.trim());
            await ensureVscNetwork();
            send.disabled = true;
            const hash = await window.ethereum.request({
              method: "eth_sendTransaction",
              params: [{ from: wallet.address, to: recipient.value.trim(), value }]
            });
            detail.textContent = "Wallet submitted transaction " + hash + ". Verifying it on VSC…";
            try {
              const saved = await api("/vsc/wallets/" + wallet.id + "/transactions/record/", { method: "POST", body: JSON.stringify({ tx_hash: hash }) });
              detail.textContent = "Transaction " + saved.status + ": " + saved.explorer_url;
            } catch (recordError) {
              detail.textContent = "MetaMask submitted the transaction. Hash: " + hash + ". Backend confirmation is pending; check the explorer before retrying.";
            }
            amount.value = "";
            recipient.value = "";
            refresh.click();
          } catch (error) {
            detail.textContent = error.message || "Transaction was not submitted.";
          } finally { send.disabled = false; }
        });
        actions.append(refresh, deposit, history, explorer);
        card.append(heading, address, actions, sendTitle, recipient, amount, send, detail);
        list.append(card);
        refresh.click();
      }
    } catch (error) {
      list.replaceChildren(element("p", "text-danger", error.message));
    }
  }
  connectButton.addEventListener("click", async () => {
    connectButton.disabled = true;
    try { await connectWallet(); }
    catch (error) { feedback.textContent = error.message || "Wallet connection failed."; }
    finally { connectButton.disabled = false; }
  });
  registerButton.addEventListener("click", async () => {
    feedback.textContent = "";
    try {
      const address = addressInput.value.trim();
      await registerAddress(address);
      feedback.textContent = "Wallet address registered.";
      await loadWallets();
    } catch (error) { feedback.textContent = error.message; }
  });
  if (window.ethereum) {
    window.ethereum.on?.("accountsChanged", accounts => {
      connectedAddress = accounts && accounts.length ? accounts[0] : "";
      connectButton.textContent = connectedAddress ? connectedAddress.slice(0, 6) + "…" + connectedAddress.slice(-4) : "Connect MetaMask";
      loadWallets();
    });
    window.ethereum.on?.("chainChanged", () => window.location.reload());
  }
  loadNetwork();
  loadWallets();
})();
