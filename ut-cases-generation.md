## TASK

指定した関数について **テスト観点一覧** と **テストケース表** を自動生成せよ。

---

## INPUT

### TARGET_FUNCTION

```
OMM::processNewsData
```

---

## CONSTRAINTS（厳守）

1. **RETRIEVAL & SOURCE FILTER**  

   - 上記関数名をキーに **ソースコードをベクトル検索**し、  
     取得したブロックを自動的に `<<SOURCE_i>>`～`<<END_SOURCE_i>>` でインジェクトせよ  
   - 各ブロックに **ターゲット関数シグネチャが “完全一致”** しない場合は破棄する  

2. **SIGNATURE FIRST**  

   1. まず `### 1. SIGNATURE & SIDE‑EFFECTS` に  
      - 引数・戻り値・例外  
      - 変更する内部/外部状態  
      - 外部呼び出し API  
        を列挙する  
   2. **以降の観点・ケース定義にはこの列挙内容のみを使用**し、  
      未列挙の識別子/API を出したら違反とみなす  

3. **TEST DESIGN STEPS**  

   - 変数初期化 / 外部依存ポイント / 条件分岐・戻り値 / メモリ操作 / 変数更新 を細分化し、網羅する。

   - 単純初期化は常にケース番号「1」  

   - 条件分岐が存在する場合、ケース番号に枝番（例：`-1`, `-2`）を追加し、各分岐を識別する  

     - 条件分岐が**ネスト**している場合は、親ケース番号を引き継ぎながら枝番をさらに連結する（例：`-1-1`）  

     - 例：  

       ```c
       if (A) {
           if (B) { D }
           else   { E }
       } else {
           C;
       }
       ```

       - `2-1-1 AかつBの場合`  
       - `2-1-2 AかつB以外の場合`  
       - `2-2   A以外の場合`

     - また、if文の中に記述されている処理が複数ある場合についても、枝番を連結する。

     - 例：

       ```c
       if (A) {
       	処理 B;
           処理 C;
       }
       ```

       - `2-1 Aの場合`
       - `2-1-1 処理Bのケース`
       - `2-1-2 処理Cのケース`

4. **ZERO‑CROSS CHECK**  

   - 出力末尾に `### CONSISTENCY_CHECK` を追加し  
     - 観点・ケース内に **SOURCE に存在しない識別子 or API** が混入していないか判定  
     - 異常があれば `INCONSISTENT_ELEMENT:` に列挙、無ければ `<None>`

5. **OUTPUT FORMAT（Markdown 固定）**

   ```md
   ### 1. SIGNATURE & SIDE‑EFFECTS
   - ...
   
   ### 2. TEST VIEWPOINTS
   - 箇条書き
   
   ### 3. TEST CASES
   | No | Test Case | Expected Result |
   |----|-----------|-----------------|
   | 1  | 変数初期化 | ... |
   | 2-1-1 | AかつBの場合 | ... |
   | 2-1-2 | AかつB以外の場合 | ... |
   | 2-2 | A以外の場合 | ... |
   
   ### CONSISTENCY_CHECK
   - INCONSISTENT_ELEMENT: <None or list>
   ```
