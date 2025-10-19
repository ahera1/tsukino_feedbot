# Tsukino Feedbot フローチャート

## デーモンモード実行フロー

```mermaid
flowchart TD
    Start([起動]) --> Init[初期化処理]
    Init --> LoadConfig[設定読み込み]
    LoadConfig --> SetupSignal[シグナルハンドラ設定<br/>SIGTERM/SIGINT]
    SetupSignal --> VerifyMastodon[Mastodon認証確認]
    
    VerifyMastodon -->|認証失敗| End([終了])
    VerifyMastodon -->|認証成功| MainLoop{メインループ}
    
    MainLoop --> CheckQuietHours{投稿禁止<br/>時間帯?}
    CheckQuietHours -->|Yes| Wait10min[10分待機]
    Wait10min --> MainLoop
    
    CheckQuietHours -->|No| CheckFeeds[フィードチェック開始]
    CheckFeeds --> LoadExisting[既存記事読み込み<br/>existing_ids作成]
    LoadExisting --> FetchFeeds[全フィードソースから<br/>記事取得]
    
    FetchFeeds --> FilterNew[新着記事フィルタリング<br/>既読チェック・日付チェック]
    FilterNew --> HasNew{新着記事<br/>あり?}
    
    HasNew -->|No| Cleanup[クリーンアップ処理]
    HasNew -->|Yes| ProcessLoop[記事処理ループ開始]
    
    ProcessLoop --> CheckShutdown1{中断要求<br/>あり?}
    CheckShutdown1 -->|Yes| StopLoop[残り記事は次回処理]
    CheckShutdown1 -->|No| SetReadAt[read_at設定]
    
    SetReadAt --> AppendArticle[existing_articlesに追加]
    AppendArticle --> SaveFirst[記事を保存<br/>既読化完了]
    SaveFirst --> ProcessAI[AI要約生成]
    
    ProcessAI --> PostMastodon[Mastodon投稿]
    PostMastodon --> SaveSecond[処理結果を再保存]
    SaveSecond --> CheckLast{最後の記事?}
    
    CheckLast -->|No| WaitLoop[待機ループ<br/>1秒×POST_WAIT回]
    WaitLoop --> CheckShutdown2{中断要求<br/>あり?}
    CheckShutdown2 -->|Yes| StopLoop
    CheckShutdown2 -->|No| ContinueWait{待機完了?}
    ContinueWait -->|No| WaitLoop
    ContinueWait -->|Yes| ProcessLoop
    
    CheckLast -->|Yes| Cleanup
    StopLoop --> Cleanup
    
    Cleanup --> CleanupOld[古い記事削除<br/>ARTICLE_RETENTION_DAYS]
    CleanupOld --> CleanupRead[古い読み取り記録削除<br/>READ_RECORD_RETENTION_DAYS]
    CleanupRead --> WaitInterval[チェック間隔まで待機<br/>CHECK_INTERVAL_MINUTES]
    
    WaitInterval --> MainLoop
```

## 記事処理の詳細フロー

```mermaid
flowchart TD
    Start([記事処理開始]) --> SetReadAt[read_at = 現在時刻]
    SetReadAt --> Append[existing_articlesに追加]
    Append --> Save1[JSONに保存<br/>既読化確定]
    
    Save1 --> AIProcess[AI要約生成]
    AIProcess --> AISuccess{要約成功?}
    
    AISuccess -->|Yes| PreparePost[投稿内容作成]
    PreparePost --> PostAPI[Mastodon API呼び出し]
    PostAPI --> PostSuccess{投稿成功?}
    
    PostSuccess -->|Yes| MarkPosted[posted_to_mastodon = True]
    PostSuccess -->|No| MarkProcessed[processed = True<br/>要約は成功]
    
    AISuccess -->|No| MarkFailed[processed = False<br/>summary = None]
    
    MarkPosted --> Save2[処理結果を再保存]
    MarkProcessed --> Save2
    MarkFailed --> Save2
    
    Save2 --> End([記事処理完了])
```

## 中断処理フロー

```mermaid
flowchart TD
    Signal([SIGTERM/SIGINT受信]) --> SetFlag[shutdown_requested = True]
    SetFlag --> LogWarning[警告ログ出力]
    
    LogWarning --> CheckPoint{現在の処理状態}
    
    CheckPoint -->|待機中| BreakWait[待機を即座に中断]
    CheckPoint -->|AI処理中| WaitAI[AI処理完了を待つ]
    CheckPoint -->|ループ先頭| BreakLoop[ループを抜ける]
    
    BreakWait --> NextCheck[次のループ先頭へ]
    WaitAI --> SaveResult[処理結果保存]
    SaveResult --> NextCheck
    
    NextCheck --> CheckLoop{ループ先頭の<br/>中断チェック}
    CheckLoop --> LogRemaining[残り記事数をログ出力]
    LogRemaining --> BreakLoop
    
    BreakLoop --> SafeExit[安全に処理を完了]
```

## データ永続化フロー

```mermaid
flowchart TD
    Start([記事保存要求]) --> PrepareBackup[バックアップファイル作成<br/>articles.json.bak]
    PrepareBackup --> Serialize[記事データをJSON化]
    
    Serialize --> WriteFile[articles.jsonに書き込み]
    WriteFile --> Success{書き込み成功?}
    
    Success -->|Yes| LogSuccess[保存完了ログ]
    Success -->|No| LogError[エラーログ]
    
    LogError --> Restore[バックアップから復元試行]
    Restore --> End([処理完了])
    LogSuccess --> End
```

## クリーンアップ処理フロー

```mermaid
flowchart TD
    Start([クリーンアップ開始]) --> LoadArticles[全記事読み込み]
    LoadArticles --> Cleanup1[通常クリーンアップ]
    
    Cleanup1 --> CalcCutoff1[基準日計算<br/>now - ARTICLE_RETENTION_DAYS]
    CalcCutoff1 --> FilterLoop1{各記事を確認}
    
    FilterLoop1 --> CheckDate1{published >= cutoff<br/>OR<br/>read_at >= cutoff?}
    CheckDate1 -->|Yes| Keep1[記事を保持]
    CheckDate1 -->|No| Remove1[記事を削除]
    
    Keep1 --> FilterLoop1
    Remove1 --> FilterLoop1
    FilterLoop1 -->|完了| Save1[フィルタ後の記事を保存]
    
    Save1 --> Cleanup2[読み取り記録クリーンアップ]
    Cleanup2 --> CalcCutoff2[基準日計算<br/>now - READ_RECORD_RETENTION_DAYS]
    CalcCutoff2 --> FilterLoop2{各記事を確認}
    
    FilterLoop2 --> CheckProcessed{processed?}
    CheckProcessed -->|No| Keep2[未処理記事は保持]
    CheckProcessed -->|Yes| CheckDate2{read_at >= cutoff?}
    
    CheckDate2 -->|Yes| Keep2
    CheckDate2 -->|No| Remove2[記事を削除]
    
    Keep2 --> FilterLoop2
    Remove2 --> FilterLoop2
    FilterLoop2 -->|完了| Save2[フィルタ後の記事を保存]
    
    Save2 --> End([クリーンアップ完了])
```

## 主要な設計判断

### 1. 既読管理
- **記事ID**: URLベースのハッシュで自動生成
- **既読判定**: `existing_ids` セットで高速チェック
- **既読化タイミング**: 処理直前（AI処理前）に `read_at` を設定して保存

### 2. 中断耐性
- **シグナルハンドラ**: SIGTERM/SIGINTを捕捉
- **処理中の記事**: 完了まで待機（AI処理と保存を完了）
- **次の記事**: ループ先頭で中断チェックし、未処理のまま終了
- **待機中**: 1秒単位で中断チェック

### 3. データ永続化
- **保存タイミング**: 
  - 記事追加時（既読化）
  - AI処理完了時（処理結果反映）
- **バックアップ**: 保存前に自動バックアップ作成
- **復元**: エラー時は自動復元を試行

### 4. クリーンアップ
- **二段階方式**:
  - 通常クリーンアップ（7日間保持）
  - 読み取り記録クリーンアップ（3日間保持）
- **未処理記事の保護**: processed=False の記事は削除しない

### 5. 待機処理
- **位置**: ループ制御下（_process_single_article の外）
- **分割チェック**: 1秒ごとに中断要求を確認
- **最終記事**: 待機をスキップ
