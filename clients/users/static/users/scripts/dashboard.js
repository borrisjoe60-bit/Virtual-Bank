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

document.querySelectorAll(".main-nav [data-nav-action]").forEach(link => {
  link.addEventListener("click", event => {
    const action = link.dataset.navAction;
    const trigger = action === "deposit" ? quickDeposit : quickTransfer;
    if (trigger) {
      event.preventDefault();
      trigger.click();
      return;
    }
    if (!document.querySelector("#account-setup")) {
      event.preventDefault();
      document.querySelector("#account-setup")?.scrollIntoView({ behavior: "smooth" });
    }
  });
});

quickTransferBtn?.addEventListener("click", async e => {
  const form = new FormData(e.target.closest("form"));
  await postData("/transfers/create/", form, false, true);
  quickTransferForm?.classList.add("d-none");
  window.location.reload();
});
quickDepositBtn?.addEventListener("click", async e => {
  const form = new FormData(e.target.closest("form"));
  await postData("/deposits/create/", form, false, true);
  quickDepositForm?.classList.add("d-none");
  window.location.reload();
});
