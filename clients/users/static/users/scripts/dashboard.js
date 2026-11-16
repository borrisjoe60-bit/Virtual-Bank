import { postData } from "./main.js";

const accountModal = document.querySelector("header + aside.account-form") || document.querySelector("aside.account-form:not(.quick-transfer-form):not(.quick-deposit-form)");
const welcomeCreateAccountBtn = document.querySelector("#welcome-create-account-btn");
const createAccountBtn = document.querySelector("#create-account-btn");
const accountNameInput = document.querySelector("#new-account-name");

function openAccountModal() {
  if (accountNameInput && !accountNameInput.value.trim()) {
    accountNameInput.value = "Savings";
  }
  accountModal?.classList.remove("d-none");
  accountNameInput?.focus();
}

welcomeCreateAccountBtn?.addEventListener("click", openAccountModal);

createAccountBtn?.addEventListener("click", async () => {
  const form = createAccountBtn.closest("form");
  if (!form || !form.reportValidity()) return;
  createAccountBtn.disabled = true;
  createAccountBtn.textContent = "Creating...";
  const result = await postData("/accounts/create-account/", new FormData(form));
  if (result?.status === "success") {
    window.location.href = "/dashboard/";
    return;
  }
  createAccountBtn.disabled = false;
  createAccountBtn.textContent = "Create";
  window.alert(result?.message || "The account could not be created. Please try again.");
});

document.querySelectorAll(".cancel-overlay-btn, #cancel-account-btn").forEach(button => {
  button.addEventListener("click", () => button.closest("aside")?.classList.add("d-none"));
});

const quickTransfer = document.querySelector(".quick-transfer");
const quickDeposit = document.querySelector(".quick-deposit");
const quickTransferForm = document.querySelector(".quick-transfer-form");
const quickDepositForm = document.querySelector(".quick-deposit-form");
const quickTransferBtn = document.getElementById("quick-transfer-btn");
const quickDepositBtn = document.getElementById("quick-deposit-btn");

quickTransfer?.addEventListener("click", () => quickTransferForm?.classList.remove("d-none"));
quickDeposit?.addEventListener("click", () => quickDepositForm?.classList.remove("d-none"));

document.querySelectorAll(".main-nav a").forEach(link => {
  link.addEventListener("click", event => {
    const action = link.dataset.navAction;
    const trigger = action === "deposit" ? quickDeposit : action === "transfer" ? quickTransfer : null;
    if (trigger) {
      event.preventDefault();
      trigger.click();
      return;
    }
    const hash = new URL(link.href, window.location.href).hash;
    const target = hash ? document.querySelector(hash) : null;
    if (!target) {
      event.preventDefault();
      const setup = document.querySelector("#account-setup");
      if (setup) setup.scrollIntoView({ behavior: "smooth", block: "center" });
      else document.querySelector("#overview")?.scrollIntoView({ behavior: "smooth" });
    }
  });
});

async function submitBankingAction(button, endpoint, overlay) {
  const formElement = button?.closest("form");
  if (!formElement || !formElement.reportValidity()) return;
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "Processing...";
  const result = await postData(endpoint, new FormData(formElement), false, true);
  const failed = result instanceof Error || !result || result.status === "failed" || result.detail || result.error || result.non_field_errors;
  if (failed) {
    button.disabled = false;
    button.textContent = originalText;
    window.alert(result?.message || result?.detail || "We could not process this request. Check the details and try again.");
    return;
  }
  overlay?.classList.add("d-none");
  window.location.reload();
}
quickTransferBtn?.addEventListener("click", () => submitBankingAction(quickTransferBtn, "/transfers/create/", quickTransferForm));
quickDepositBtn?.addEventListener("click", () => submitBankingAction(quickDepositBtn, "/deposits/create/", quickDepositForm));
