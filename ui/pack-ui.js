const PackUI = (() => {
  let activePlan = null;
  let clipboardRequest = null;
  let library = { packs: [], profiles: {} };
  const request = async (method, ...args) => {
    try { return await api[method](...args); }
    catch (error) { return { error: "This operation couldn't finish. Please try again." }; }
  };
  const failed = result => {
    if (result?.error) { toast(result.error, "bad"); return true; }
    return false;
  };
  function onModal(keep = null) {
    if (activePlan && activePlan !== keep) request("cancel_plan", activePlan);
    activePlan = keep;
  }
  const fileList = files => `<div class="pk-file-list">${files.map(file => `<div>${esc(file.startsWith("Assets/") ? file : "custom_scripts/" + file)}</div>`).join("")}</div>`;

  function linkInstall(url = "", start = false, updateId = null, attachmentNames = []) {
    modal(`<h2>${updateId ? "Update pack from Discord" : "Get mods &amp; assets from Discord"}</h2>
      <div class="body"><p>Open a post in your existing Discord desktop session, or paste its link.</p>
        <div class="row"><button class="btn" id="ln-forum">Open #mods</button><button class="btn" id="ln-assets">Open #assets</button></div></div>
      <div class="field"><label for="ln-url">Discord post or file link</label><input class="input" id="ln-url" value="${esc(url)}" placeholder="Paste a Discord link"></div>
      <div id="ln-pick"></div><div class="pk-error" id="ln-err"></div>
      <div class="actions"><button class="btn ghost" onclick="closeModal()">Cancel</button><button class="btn primary" id="ln-go">Download</button></div>`);
    const field = $("#ln-url"), button = $("#ln-go"), pick = $("#ln-pick"), error = $("#ln-err");
    let generation = 0;
    const busy = (on, text = "Downloading…") => { button.disabled = on; button.textContent = on ? text : "Download"; };
    const discard = result => { if (result?.job) request("cancel_post_link", result.job); if (result?.token) request("cancel_plan", result.token); if (result?.plan?.token) request("cancel_plan", result.plan.token); };
    async function download(urls, source) {
      const current = ++generation;
      busy(true); error.textContent = "";
      const result = await request("link_files", urls, source, updateId);
      if (!field.isConnected || current !== generation) { discard(result); return; }
      if (result?.error) { error.textContent = result.error; busy(false); return; }
      installPack(result, true);
    }
    function choose(files, source) {
      stopPostImport(); busy(false);
      if (files.length === 1) { download([files[0].url], source); return; }
      const matches = files.filter(file => attachmentNames.includes(file.name));
      const selected = new Set((matches.length ? matches : files).slice(0, 20).map(file => file.url));
      pick.innerHTML = `<p class="muted">Select up to 20 attachments to install together as one pack.</p>
        <div class="pk-file-list">${files.map((file, index) => `<label class="pk-attachment"><input type="checkbox" data-file="${index}" ${selected.has(file.url) ? "checked" : ""}><span>${esc(file.name)}</span></label>`).join("")}</div>`;
      button.textContent = "Review selected";
      button.onclick = () => {
        const urls = $$("#ln-pick input:checked").map(input => files[Number(input.dataset.file)].url);
        if (!urls.length) { error.textContent = "Select at least one attachment."; return; }
        download(urls, source);
      };
    }
    async function startPostDownload(pending, indices) {
      pending.selectionSent = true;
      busy(true, "Downloading…");
      pick.innerHTML = `<p id="ln-post-status"><span class="spin"></span> Starting the attachment download…</p>`;
      const result = await request("select_post_attachments", pending.id, indices, updateId);
      if (pendingPostImport !== pending || !field.isConnected) { discard(result); return; }
      if (result?.error) { stopPostImport(); pick.innerHTML = ""; error.textContent = result.error; busy(false); }
    }
    async function choosePost(pending, post) {
      if (pending.awaitingSelection || pending.selectionSent) return;
      const files = [...(post.files || []), ...(post.previews || [])];
      if (files.length === 1) { await startPostDownload(pending, [0]); return; }
      pending.awaitingSelection = true;
      const matches = files.map((file, index) => attachmentNames.includes(file.name) ? index : -1).filter(index => index >= 0);
      const selected = new Set((matches.length ? matches : files.map((_, index) => index)).slice(0, 20));
      pick.innerHTML = `<p class="muted">Select up to 20 attachments. Code previews download automatically too.</p><div class="pk-file-list">${files.map((file, index) => `<label class="pk-attachment"><input type="checkbox" data-index="${index}" ${selected.has(index) ? "checked" : ""}><span>${esc(file.name)}</span></label>`).join("")}</div>`;
      button.disabled = false; button.textContent = "Download selected";
      button.onclick = () => {
        const indices = $$("#ln-pick input:checked").map(input => Number(input.dataset.index));
        if (!indices.length || indices.length > 20) { error.textContent = "Select between 1 and 20 attachments."; return; }
        startPostDownload(pending, indices);
      };
    }
    async function get(link) {
      stopPostImport(); pick.innerHTML = "";
      const current = ++generation;
      busy(true, "Opening…"); error.textContent = "";
      button.onclick = () => get(field.value);
      const result = await request("link_mod", link, null, updateId);
      if (!field.isConnected || current !== generation) { discard(result); return; }
      if (result?.error) { error.textContent = result.error; busy(false); return; }
      if (result.kind === "post") {
        busy(false);
        pick.innerHTML = `<p id="ln-post-status"><span class="spin"></span> Finding attachments in Discord…</p>`;
        const pending = { id: result.job, timer: null, polling: false };
        pendingPostImport = pending;
        const poll = async () => {
          if (pendingPostImport !== pending || !field.isConnected || pending.polling) return;
          pending.polling = true;
          try {
            const post = await request("post_link_status", pending.id, updateId);
            if (pendingPostImport !== pending || !field.isConnected) { if (post?.plan) discard(post.plan); return; }
            if (post.error || ["error", "cancelled"].includes(post.status) || (post.status === "empty" && !post.waiting)) {
              stopPostImport(); pick.innerHTML = ""; error.textContent = post.error || post.message || "Post lookup stopped.";
            } else if (post.status === "downloaded") {
              installPack(post.plan, true);
            } else if (post.status === "downloading") {
              button.disabled = true; button.textContent = "Downloading…";
              if (!$("#ln-post-status")) pick.innerHTML = `<p id="ln-post-status"></p>`;
              $("#ln-post-status").textContent = post.message;
            } else if (post.status === "needs_file") {
              if (!pending.fallbackShown) {
                pending.fallbackShown = true;
                pick.innerHTML = `<p id="ln-post-status"></p><div class="pk-file-list">${(post.previews || []).map(file => `<div>${esc(file.name)}</div>`).join("")}</div>`;
                button.disabled = false;
                button.textContent = "Choose downloaded file…";
                button.onclick = async () => {
                  if (pending.polling) return;
                  pending.polling = true; button.disabled = true;
                  try {
                    const plan = await request("pick_preview_download", pending.id, updateId);
                    if (pendingPostImport !== pending || !field.isConnected) { discard(plan); return; }
                    if (plan?.error) error.textContent = plan.error;
                    else if (plan) installPack(plan, true);
                  } finally { pending.polling = false; if (button.isConnected) button.disabled = false; }
                };
              }
              $("#ln-post-status").textContent = post.message;
            } else if (post.status === "preview" || (post.status === "ready" && post.previews?.length)) {
              await choosePost(pending, post);
            } else if (post.status === "ready") {
              choose(post.files, post.post_url || link);
            } else $("#ln-post-status").textContent = post.message || "Waiting for the selected post…";
          } finally { pending.polling = false; }
        };
        pending.timer = setInterval(poll, 900); poll(); return;
      }
      if (result.kind === "choose") { choose(result.files, link); return; }
      installPack(result, true);
    }
    field.oninput = () => { stopPostImport(); generation++; pick.innerHTML = ""; busy(false); button.onclick = () => get(field.value); };
    field.onpaste = event => {
      const text = (event.clipboardData?.getData("text") || "").trim();
      if (DISCORD_FILE.test(text) || DISCORD_MESSAGE.test(text)) { event.preventDefault(); field.value = text; get(text); }
    };
    field.onkeydown = event => { if (event.key === "Enter") button.click(); };
    $("#ln-forum").onclick = () => { field.value = S.ov.modsForumUrl; get(field.value); };
    $("#ln-assets").onclick = () => { field.value = S.ov.assetsForumUrl; get(field.value); };
    button.onclick = () => get(field.value);
    if (start) get(url);
  }

  async function addMods(files) {
    files = files || await api.pick_mod_files();
    if (!files?.length) return;
    const result = await request("prepare_files", files.map(file => file.path));
    if (!failed(result)) installPack(result);
  }

  function pasteFiles() {
    if (clipboardRequest) return clipboardRequest;
    clipboardRequest = (async () => {
      const result = await request("prepare_clipboard_files");
      if (!result || failed(result)) return false;
      // A file review must not replace another dialog opened while the file was being read.
      if ($("#overlay").classList.contains("show")) {
        await request("cancel_plan", result.token);
        return false;
      }
      await installPack(result);
      return true;
    })().finally(() => { clipboardRequest = null; });
    return clipboardRequest;
  }

  async function installPack(plan, fromLink = false) {
    plan = plan || await request("pick_pack");
    if (!plan || failed(plan)) return;
    const mods = plan.mods || [], assets = plan.assets || [];
    const kind = plan.content_kind || (mods.length && assets.length ? "mixed" : assets.length ? "assets" : mods.length ? "mods" : "empty");
    const assetCount = plan.detected_asset_count ?? assets.length;
    const noun = kind === "mods" ? mods.length === 1 ? "mod" : "mods" : kind === "assets" ? assetCount === 1 ? "asset" : "assets" : "pack";
    const targetPage = plan.content_page || (kind === "assets" ? "assets" : kind === "mods" ? "mods" : "packs");
    const detected = [mods.length ? `${mods.length} GSC/GSCC mod${mods.length === 1 ? "" : "s"}` : "", assetCount ? `${assetCount} asset${assetCount === 1 ? "" : "s"}` : ""].filter(Boolean).join(" + ");
    const folderFields = (plan.destinations || []).map(item => `<div class="field"><label>${esc(item.name)} destination</label><select class="input pk-destination" data-index="${esc(item.index)}"><option value="">Choose a folder…</option>${item.folders.map(folder => `<option value="${esc(folder)}" ${item.selected === folder ? "selected" : ""}>Assets/${esc(folder)}</option>`).join("")}</select></div>`).join("");
    go(targetPage);
    modal(`<h2>${plan.update_id ? "Update" : "Install"} ${noun}</h2>
      <div class="field"><label for="pk-name">Pack name</label><input class="input" id="pk-name" maxlength="120" value="${esc(plan.reviewName || plan.name)}"></div>
      <div class="body">
        <p><b>${detected ? `Detected automatically: ${detected}` : "No supported files found"}</b></p>
        ${mods.length ? `<p class="muted">GSC/GSCC mods go into custom_scripts.</p>` : ""}
        ${assets.length ? `<p class="muted">Asset folders were detected from the files${kind === "mixed" ? "; both types will be installed together" : ""}.</p>` : ""}
        ${plan.unresolved ? `<p class="muted">This is an asset, but its file type fits several folders. Choose its destination to continue.</p>${folderFields}` : folderFields ? `<details class="pk-review-details"><summary>Change asset folders</summary>${folderFields}</details>` : ""}
        ${kind === "mixed" ? `<h3>Mods</h3>${fileList(mods)}<h3>Assets</h3>${fileList(assets)}` : fileList(plan.files || [])}
        ${plan.conflicts?.length ? `<details class="pk-review-details"><summary>Shared or existing files (${plan.conflicts.length})</summary><div class="pk-file-list">${plan.conflicts.map(item => `<div><b>${esc(item.path)}</b><small>Current: ${esc(item.active)}${item.owners.length ? ` · Packs: ${esc(item.owners.join(", "))}` : ""}${item.same ? " · Identical content" : ""}</small></div>`).join("")}</div></details>` : ""}
        ${plan.removed?.length ? `<details class="pk-review-details"><summary>${plan.removed.length} file(s) removed by this update</summary>${fileList(plan.removed)}</details>` : ""}
        ${plan.bad?.length ? `<details class="pk-review-details"><summary>Skipped files (${plan.bad.length})</summary><div class="pk-file-list">${plan.bad.map(text => `<div>${esc(text)}</div>`).join("")}</div></details>` : ""}
        ${plan.existing?.length ? `<label class="pk-attachment"><input type="checkbox" id="pk-over"><span>Replace ${plan.existing.length} existing file(s); originals are retained</span></label>` : ""}
        ${mods.length ? `<label class="pk-attachment"><input type="checkbox" id="pk-preset"><span>Also save source mods as a preset</span></label>` : ""}
        <p class="muted">You can disable or uninstall the complete pack from Packs.</p></div>
      <div class="pk-error" id="pk-error"></div><div class="actions"><button class="btn ghost" onclick="closeModal()">Cancel</button><button class="btn primary" id="pk-go" ${!plan.files?.length || plan.unresolved ? "disabled" : ""}>${plan.update_id ? "Update" : "Install"} ${noun}</button></div>`, plan.token);
    let revision = 0;
    $$(".pk-destination").forEach(select => select.onchange = async () => {
      const current = ++revision;
      const reviewName = $("#pk-name").value;
      const folders = Object.fromEntries($$(".pk-destination").map(item => [item.dataset.index, item.value]));
      const updated = await request("revise_plan", plan.token, folders);
      if (!select.isConnected || current !== revision) return;
      if (!failed(updated)) { updated.reviewName = reviewName; installPack(updated, fromLink); }
    });
    $("#pk-go").onclick = async () => {
      const button = $("#pk-go"), error = $("#pk-error"); button.disabled = true;
      const result = await request("install_pack", plan.token, $("#pk-over")?.checked ? plan.existing : [], $("#pk-preset")?.checked || false, $("#pk-name").value);
      if (result?.error) { if (error.isConnected) { error.textContent = result.error; button.disabled = false; } return; }
      if (result.assets) AS.openGroups.add("managed:" + result.id);
      activePlan = null; closeModal(); await refresh();
      modal(`<h2>${plan.update_id ? "Updated" : "Installed"} “${esc(result.name)}”</h2><div class="body"><p>${result.mods} source mod(s) and ${result.assets} asset(s) in this pack.${result.skipped ? ` ${result.skipped} existing file(s) skipped.` : ""}</p>
        ${result.recovery ? `<p>Changes made outside Kronos Plus were retained in:<br><span class="muted">${esc(result.recovery)}</span></p>` : ""}${result.warning ? `<p>${esc(result.warning)}</p>` : ""}</div>
        <div class="actions"><button class="btn" id="pk-manage">Manage pack</button><button class="btn primary" onclick="closeModal()">Done</button></div>`);
      $("#pk-manage").onclick = () => { closeModal(); go("packs"); };
    };
  }

  async function load() {
    const result = await request("managed_packs");
    if (result?.error) { $("#pack-list").innerHTML = `<div class="card">${esc(result.error)}</div>`; return; }
    library = result;
    $("#nav-packs").textContent = result.packs.length;
    const selected = $("#full-profile").value;
    const profiles = Object.keys(result.profiles).sort();
    $("#full-profile").innerHTML = `<option value="">Choose a full profile…</option>${profiles.map(name => `<option value="${esc(name)}" ${name === selected ? "selected" : ""}>${esc(name)}</option>`).join("")}`;
    $("#profile-apply").disabled = $("#profile-delete").disabled = !profiles.length;
    $("#pack-list").innerHTML = result.packs.length ? result.packs.map(pack => `<article class="card pk-card" data-pack="${esc(pack.id)}">
      <div class="row"><h3>${icon("folder")}${esc(pack.name)}</h3><span class="pk-state ${pack.enabled ? "on" : ""}">${pack.enabled ? "Enabled" : "Disabled"}</span></div>
      <p class="muted">${pack.mods} source mod(s) · ${pack.assets} asset(s) · ${pack.files.length} file(s)</p>
      ${pack.conflicts.length ? `<p class="pk-conflict">${pack.conflicts.length} shared file(s). Pack priority picks which version is used</p>` : ""}
      ${pack.modified.length ? `<p class="pk-conflict">${pack.modified.length} file(s) changed outside Kronos Plus</p>` : ""}
      <div class="row pk-actions"><button class="btn sm" data-action="toggle">${pack.enabled ? "Disable" : "Enable"}</button><button class="btn sm" data-action="details">Files &amp; conflicts</button>
        <button class="btn sm" data-action="update">${pack.source_post ? "Update from Discord" : "Link Discord post"}</button><button class="btn sm danger" data-action="uninstall">Uninstall pack</button></div></article>`).join("")
      : `<div class="card empty">${icon("folder")}<div>No managed packs yet. Install files or get a pack from Discord.</div></div>`;
    $$("#pack-list [data-action]").forEach(button => button.onclick = () => {
      const pack = result.packs.find(item => item.id === button.closest("[data-pack]").dataset.pack);
      if (button.dataset.action === "details") details(pack.id);
      else if (button.dataset.action === "update") pack.source_post ? linkInstall(pack.source_post, true, pack.id, pack.attachments) : setSource(pack);
      else change(pack.id, button.dataset.action === "toggle" ? pack.enabled ? "disable" : "enable" : "uninstall");
    });
  }

  async function details(identity) {
    const result = await request("managed_packs");
    if (failed(result)) return;
    const pack = result.packs.find(item => item.id === identity);
    if (!pack) return toast("That pack is no longer installed", "bad");
    modal(`<h2>${esc(pack.name)}</h2><div class="body"><p>${pack.enabled ? "Enabled" : "Disabled"} · ${pack.files.length} file(s)</p>${fileList(pack.files)}
      ${pack.conflicts.length ? `<h3>Shared files</h3><div class="pk-file-list">${pack.conflicts.map(item => `<div><b>${esc(item.path)}</b><small>Packs: ${esc(item.packs.join(", "))}<br>Active: ${esc(item.active)}</small></div>`).join("")}</div>` : ""}
      ${pack.modified.length ? `<h3>Changed outside the app</h3>${fileList(pack.modified)}` : ""}
      <p class="muted">${pack.source_post ? "Updates use the original Discord post and let you review attachments before replacing files." : "Link a Discord post to enable updates for this pack."}</p></div>
      <div class="actions"><button class="btn" id="pk-source">${pack.source_post ? "Change Discord source" : "Link Discord post"}</button><button class="btn primary" onclick="closeModal()">Done</button></div>`);
    $("#pk-source").onclick = () => setSource(pack);
  }

  async function change(identity, action) {
    const preview = await request("pack_action_preview", identity, action);
    if (failed(preview)) return;
    const verb = { enable: "Enable", disable: "Disable", uninstall: "Uninstall" }[action];
    const body = `<p>${verb} <b>${esc(preview.pack.name)}</b> (${preview.files} files)?</p>
      <p>${action === "uninstall" ? "The pack is removed from the library. Its files fall back to another enabled pack or to the originals saved before installation." : "Pack priority determines which version of a shared file is used. Saved originals return when no enabled pack supplies that file."}</p>
      ${preview.modified.length ? `<p>${preview.modified.length} changed file(s) will be copied to a recovery folder before this operation.</p>${fileList(preview.modified)}` : ""}
      ${preview.conflicts.length ? `<details class="pk-review-details"><summary>Shared files (${preview.conflicts.length})</summary><div class="pk-file-list">${preview.conflicts.map(item => `<div>${esc(item.path)}<small>Current: ${esc(item.active)}<br>After this action: ${esc(item.nextActive || item.active)}</small></div>`).join("")}</div></details>` : ""}`;
    if (!(await confirmBox(`${verb} pack?`, body, `${verb} pack`, action === "uninstall"))) return;
    const result = await request("pack_action", identity, action);
    if (failed(result)) return;
    toast(`${preview.pack.name}: ${action === "enable" ? "enabled" : action === "disable" ? "disabled" : "uninstalled"}`, "ok");
    await refresh();
    if (result.recovery) modal(`<h2>Changed files retained</h2><div class="body">Copies are stored in:<p class="muted">${esc(result.recovery)}</p></div><div class="actions"><button class="btn primary" onclick="closeModal()">Done</button></div>`);
  }

  function setSource(pack) {
    modal(`<h2>Discord source for ${esc(pack.name)}</h2><div class="body">Paste a specific Kronos mod or asset post link.</div><div class="field"><input class="input" id="pack-source" value="${esc(pack.source_post || "")}" placeholder="https://discord.com/channels/…"></div><div class="pk-error" id="pack-source-error"></div>
      <div class="actions"><button class="btn ghost" onclick="closeModal()">Cancel</button><button class="btn primary" id="pack-source-save">Save source</button></div>`);
    $("#pack-source-save").onclick = async () => {
      const result = await request("pack_source", pack.id, $("#pack-source").value);
      if (result?.error) { $("#pack-source-error").textContent = result.error; return; }
      closeModal(); load();
    };
  }

  function saveProfile() {
    modal(`<h2>Save full profile</h2><div class="body">Saves enabled source mods, enabled packs, and pack priority. Asset packs include their HUD themes and icons.</div>
      <div class="field"><label for="full-profile-name">Profile name</label><input class="input" id="full-profile-name" maxlength="120" placeholder="e.g. My Zombies setup"></div><div class="pk-error" id="profile-error"></div>
      <div class="actions"><button class="btn ghost" onclick="closeModal()">Cancel</button><button class="btn primary" id="profile-save">Save profile</button></div>`);
    $("#profile-save").onclick = async () => {
      const name = $("#full-profile-name").value.trim();
      if (!name) { $("#profile-error").textContent = "Enter a profile name."; return; }
      if (library.profiles[name] && !(await confirmBox("Replace profile?", `Replace <b>${esc(name)}</b> with the current setup?`, "Replace"))) return;
      const result = await request("save_full_profile", name);
      if (failed(result)) return;
      closeModal(); toast("Full profile saved", "ok"); load();
    };
  }

  function init() {
    $("#pack-add").onclick = () => installPack();
    $("#pack-get").onclick = () => linkInstall();
    $("#profile-save-current").onclick = saveProfile;
    $("#profile-apply").onclick = async () => {
      const name = $("#full-profile").value;
      if (!name) return;
      if (!(await confirmBox("Apply full profile?", `Switch enabled mods and packs to <b>${esc(name)}</b>?`, "Apply profile"))) return;
      const result = await request("apply_full_profile", name);
      if (failed(result)) return;
      toast("Full profile applied", "ok"); refresh();
    };
    $("#profile-delete").onclick = async () => {
      const name = $("#full-profile").value;
      if (!name || !(await confirmBox("Delete profile?", `Delete <b>${esc(name)}</b>? Your current files stay as they are.`, "Delete", true))) return;
      if (!failed(await request("delete_full_profile", name))) load();
    };
  }
  return { init, load, details, linkInstall, installPack, addMods, pasteFiles, onModal, release: () => onModal(null) };
})();
