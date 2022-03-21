# Artichoke Server
歡迎來到 artichoke server 的專案！在開始工作前，麻煩請先閱讀下列開發流程細節後，再開始進行開發，感謝！

## 開發流程

### 新功能 (`New Feature`)

1. 從 develop 開一個新的 feature branch，branch 名稱需讓人看得懂是做什麼新功能。(e.g. update-readme)
2. 新功能需在 feature branch 上進行實作，**不可** 直接推進 develop branch。
3. 開發完成後，需進行測試後才可進行下一步。
4. 完成後，推到 gitlab 上，並發出 Merge Request (以下簡稱 **MR**) 給 reviewer，並告知 reviewer 進行 code review，且 MR 的 **Description** 格式須符合以下：
    - [WHAT] 做了什麼主要改動
    - [CHANGES] 稍微描述做了什麼事情
6. Merge 進 develop 後，在 `Develop branch` 打 tag，並在 tag 的內容中以下列格式描述：
    - {版號}
    - [WHAT] 做了什麼主要改動
    - [CHANGES] 稍微描述做了什麼事情
    - [DOCKER] 目前所有的 Docker 版本
7. 以跟上面 tag 相同的格式發出 **MR** 到 master，並指定給 PM 進行 review。
8. 待 PM review 完成後，即可 merge 至 master。

---

### 緊急修正 (`Hotfix`)

1. 從 master 開一個新的 hotfix branch，branch 名稱需讓人看得懂是做什麼新功能。(e.g. hotfix-edit-readme)
2. Hotfix 修正完成後，需進行測試後才可進行下一步。
3. 完成後，推到 gitlab 上，並發出 MR 給 reviewer，並告知 reviewer 進行 code review，且 MR 的 **Description** 格式須符合以下：
    - [WHAT] [Hotfix] 做了什麼緊急修正
    - [CHANGES] 稍微描述做了什麼事情
4. 在 `Hotfix branch` 上打 tag，並在 tag 的內容中以下列格式描述：
    - {版號}
    - [WHAT] [Hotfix] 做了什麼緊急修正
    - [CHANGES] 稍微描述做了什麼事情
    - [DOCKER] 目前所有的 Docker 版本
5. 以跟上面 tag 相同的格式發出 **MR** 到 `develop`, `master`，並分別指定給 其他RD, PM 進行 review。
6. 待 review 完成後，即可 merge 至 develop, master。

---

## 進版流程

1. 進版須由負責人員進行上版，若有新版本需更新，請告知負責人員進行上版。
2. 連線至小 asus 機器 (10.101.218.245) 並切至 artichoke_server repo (指令: `cd /usr/local/src/git/artichoke_server`)
3. 將版本更新至 master 最新版，(指令: git pull)。
4. 需注意 `artichoke_base_service.ini` 檔案是否有修正；若有，則需更新 asus 上修改後的 config 檔上。