## bronze/tiktok_video (2 rows)

```
shape: (2, 16)
┌────────────┬────────────┬────────────┬────────────┬────────────┬────────────┬────────────┬────────────┬────────────┬────────────┬──────────┬─────────┬──────────┬──────────┬────────────┬────────────┐
│ video_id   ┆ url        ┆ s3_key     ┆ sha256     ┆ size_bytes ┆ duration_s ┆ keyword    ┆ fetched_at ┆ title      ┆ creator    ┆ revenue  ┆ views   ┆ ads_roas ┆ ai_video ┆ product_na ┆ category_n │
│ ---        ┆ ---        ┆ ---        ┆ ---        ┆ ---        ┆ ---        ┆ ---        ┆ ---        ┆ ---        ┆ ---        ┆ ---      ┆ ---     ┆ ---      ┆ ---      ┆ me         ┆ ame        │
│ str        ┆ str        ┆ str        ┆ str        ┆ null       ┆ i64        ┆ str        ┆ i64        ┆ str        ┆ str        ┆ f64      ┆ i64     ┆ f64      ┆ i64      ┆ ---        ┆ ---        │
│            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ str        ┆ str        │
╞════════════╪════════════╪════════════╪════════════╪════════════╪════════════╪════════════╪════════════╪════════════╪════════════╪══════════╪═════════╪══════════╪══════════╪════════════╪════════════╡
│ 7581164199 ┆ https://ww ┆ beyond-vid ┆ f684cd1cf0 ┆ null       ┆ 62         ┆ portable   ┆ 1787326544 ┆ I’m still  ┆ kdegraw15  ┆ 32697.62 ┆ 1939986 ┆ 2.67     ┆ 0        ┆ Portable   ┆ Body       │
│ 045319967  ┆ w.tiktok.c ┆ eos/trendi ┆ 1dede3974f ┆            ┆            ┆ nebulizer  ┆            ┆ shocked to ┆            ┆          ┆         ┆          ┆          ┆ Mesh       ┆ Beauty     │
│            ┆ om/@kdegra ┆ ng_tiktok_ ┆ ff17b9ebfc ┆            ┆            ┆            ┆            ┆ see the    ┆            ┆          ┆         ┆          ┆          ┆ Nebulizer  ┆ Devices    │
│            ┆ w15/video/ ┆ videos/lan ┆ 4f35a46d90 ┆            ┆            ┆            ┆            ┆ comparison ┆            ┆          ┆         ┆          ┆          ┆ with Auto- ┆            │
│            ┆ 7581164199 ┆ ding/Body_ ┆ 887551ea07 ┆            ┆            ┆            ┆            ┆ from this  ┆            ┆          ┆         ┆          ┆          ┆ Cleaning,  ┆            │
│            ┆ 045319967  ┆ Beauty_Dev ┆ cf3258dbf2 ┆            ┆            ┆            ┆            ┆ portable,  ┆            ┆          ┆         ┆          ┆          ┆ Whisper-Qu ┆            │
│            ┆            ┆ ices/Porta ┆ 625b       ┆            ┆            ┆            ┆            ┆ quiet,     ┆            ┆          ┆         ┆          ┆          ┆ iet        ┆            │
│            ┆            ┆ ble_Mesh_N ┆            ┆            ┆            ┆            ┆            ┆ small rech ┆            ┆          ┆         ┆          ┆          ┆ Operation  ┆            │
│            ┆            ┆ ebulizer_w ┆            ┆            ┆            ┆            ┆            ┆ argeable   ┆            ┆          ┆         ┆          ┆          ┆ & LED      ┆            │
│            ┆            ┆ ith_Auto-C ┆            ┆            ┆            ┆            ┆            ┆ nebulizer  ┆            ┆          ┆         ┆          ┆          ┆ Interface, ┆            │
│            ┆            ┆ leaning_Wh ┆            ┆            ┆            ┆            ┆            ┆ and        ┆            ┆          ┆         ┆          ┆          ┆ Rechargeab ┆            │
│            ┆            ┆ isper-Quie ┆            ┆            ┆            ┆            ┆            ┆ compare it ┆            ┆          ┆         ┆          ┆          ┆ le         ┆            │
│            ┆            ┆ t_Ope/2026 ┆            ┆            ┆            ┆            ┆            ┆ to a       ┆            ┆          ┆         ┆          ┆          ┆ Handheld   ┆            │
│            ┆            ┆ -08-21/I_m ┆            ┆            ┆            ┆            ┆            ┆ urgent     ┆            ┆          ┆         ┆          ┆          ┆ Mist       ┆            │
│            ┆            ┆ _still_sho ┆            ┆            ┆            ┆            ┆            ┆ care       ┆            ┆          ┆         ┆          ┆          ┆ Device for ┆            │
│            ┆            ┆ cked_to_se ┆            ┆            ┆            ┆            ┆            ┆ nebulizer! ┆            ┆          ┆         ┆          ┆          ┆ Adults &   ┆            │
│            ┆            ┆ e_the_comp ┆            ┆            ┆            ┆            ┆            ┆ These are  ┆            ┆          ┆         ┆          ┆          ┆ Kids, Rech ┆            │
│            ┆            ┆ arison_fro ┆            ┆            ┆            ┆            ┆            ┆ so perfect ┆            ┆          ┆         ┆          ┆          ┆ argeable   ┆            │
│            ┆            ┆ m_this_por ┆            ┆            ┆            ┆            ┆            ┆ to have at ┆            ┆          ┆         ┆          ┆          ┆ Mesh       ┆            │
│            ┆            ┆ table_q_75 ┆            ┆            ┆            ┆            ┆            ┆ 2am when   ┆            ┆          ┆         ┆          ┆          ┆ Nebulizer, ┆            │
│            ┆            ┆ …          ┆            ┆            ┆            ┆            ┆            ┆ you need   ┆            ┆          ┆         ┆          ┆          ┆ Usb Rechar ┆            │
│            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆ it or even ┆            ┆          ┆         ┆          ┆          ┆ geable     ┆            │
│            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆ …          ┆            ┆          ┆         ┆          ┆          ┆ Nebulizer  ┆            │
│ 7669988712 ┆ https://ww ┆ beyond-vid ┆ e9614cf69b ┆ null       ┆ 8          ┆ electric   ┆ 1787325217 ┆ These are  ┆ cassiesuni ┆ 39905.31 ┆ 1948917 ┆ 3.51     ┆ 0        ┆ Akunbem    ┆ Body       │
│ 033373471  ┆ w.tiktok.c ┆ eos/trendi ┆ b5851eb5f5 ┆            ┆            ┆ shaver     ┆            ┆ genius     ┆ quepicks   ┆          ┆         ┆          ┆          ┆ Bikini     ┆ Beauty     │
│            ┆ om/@cassie ┆ ng_tiktok_ ┆ 93db29100a ┆            ┆            ┆            ┆            ┆ @Frost     ┆            ┆          ┆         ┆          ┆          ┆ Trimmer    ┆ Devices    │
│            ┆ suniquepic ┆ videos/lan ┆ b2e1af8adb ┆            ┆            ┆            ┆            ┆ Buddy  #to ┆            ┆          ┆         ┆          ┆          ┆ for Women, ┆            │
│            ┆ ks/video/7 ┆ ding/Body_ ┆ 4aac10ca84 ┆            ┆            ┆            ┆            ┆ ktokshopcr ┆            ┆          ┆         ┆          ┆          ┆ Electric   ┆            │
│            ┆ 6699887120 ┆ Beauty_Dev ┆ f004125240 ┆            ┆            ┆            ┆            ┆ eatorpicks ┆            ┆          ┆         ┆          ┆          ┆ Shaver and ┆            │
│            ┆ 33373471   ┆ ices/Akunb ┆ 7462       ┆            ┆            ┆            ┆            ┆ #TikTokMad ┆            ┆          ┆         ┆          ┆          ┆ Razor Rech ┆            │
│            ┆            ┆ em_Bikini_ ┆            ┆            ┆            ┆            ┆            ┆ eMeBuyIt   ┆            ┆          ┆         ┆          ┆          ┆ argeable   ┆            │
│            ┆            ┆ Trimmer_fo ┆            ┆            ┆            ┆            ┆            ┆ #babyessen ┆            ┆          ┆         ┆          ┆          ┆ 2-in-1     ┆            │
│            ┆            ┆ r_Women_El ┆            ┆            ┆            ┆            ┆            ┆ tials      ┆            ┆          ┆         ┆          ┆          ┆ Body and   ┆            │
│            ┆            ┆ ectric_Sha ┆            ┆            ┆            ┆            ┆            ┆ #coolfinds ┆            ┆          ┆         ┆          ┆          ┆ Facial     ┆            │
│            ┆            ┆ ver_and_Ra ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ Epilator,  ┆            │
│            ┆            ┆ zor_R/2026 ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ Dual Heads ┆            │
│            ┆            ┆ -08-21/The ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ for        ┆            │
│            ┆            ┆ se_are_gen ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ Painless   ┆            │
│            ┆            ┆ ius_Frost_ ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ Trimming   ┆            │
│            ┆            ┆ Buddy_tokt ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ of Pubic   ┆            │
│            ┆            ┆ okshopcrea ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ Hair,      ┆            │
│            ┆            ┆ torpicks_T ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ Face,      ┆            │
│            ┆            ┆ ikTokMa_76 ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ Underarms  ┆            │
│            ┆            ┆ …          ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ and Legs,  ┆            │
│            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ IPX7 Water ┆            │
│            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ proof.     ┆            │
│            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆            ┆          ┆         ┆          ┆          ┆ Chr…       ┆            │
└────────────┴────────────┴────────────┴────────────┴────────────┴────────────┴────────────┴────────────┴────────────┴────────────┴──────────┴─────────┴──────────┴──────────┴────────────┴────────────┘
```

## silver/video_storyboard (10 rows)

```
shape: (10, 12)
┌───────────────────┬────────────────┬──────────┬─────────┬───────┬─────────────────┬───────────────────┬──────────────────┬──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ video_id          ┆ prompt_version ┆ scene_no ┆ t_start ┆ t_end ┆ shot_type       ┆ visual            ┆ on_screen_text   ┆ voiceover        ┆ hook             ┆ cta              ┆ summary          │
│ ---               ┆ ---            ┆ ---      ┆ ---     ┆ ---   ┆ ---             ┆ ---               ┆ ---              ┆ ---              ┆ ---              ┆ ---              ┆ ---              │
│ str               ┆ str            ┆ i64      ┆ f64     ┆ f64   ┆ str             ┆ str               ┆ str              ┆ str              ┆ str              ┆ str              ┆ str              │
╞═══════════════════╪════════════════╪══════════╪═════════╪═══════╪═════════════════╪═══════════════════╪══════════════════╪══════════════════╪══════════════════╪══════════════════╪══════════════════╡
│ 75811641990453199 ┆ storyboard-v1  ┆ 1        ┆ 0.0     ┆ 3.8   ┆ close-up        ┆ A woman in        ┆ Comparing a      ┆ If you have ever ┆ An urgent care   ┆ I'm gonna link   ┆ An urgent care   │
│ 67                ┆                ┆          ┆         ┆       ┆                 ┆ medical scrubs    ┆ plug-in,         ┆ needed a         ┆ physician        ┆ this down below  ┆ healthcare       │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ showcases a       ┆ hospital grade   ┆ nebulizer, this  ┆ assistant        ┆ because this is  ┆ provider         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ compact handheld  ┆ nebulizer vs     ┆ is the one that  ┆ compares a       ┆ something that   ┆ demonstrates why │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ nebulizer         ┆ portable         ┆ you need to get. ┆ noisy,           ┆ you're gonna     ┆ a quiet,         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ releasing mist    ┆ nebulizer        ┆                  ┆ traditional      ┆ wanna have at 2  ┆ rechargeable     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ directly toward   ┆                  ┆                  ┆ hospital         ┆ o'clock in the   ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ the camera.       ┆                  ┆                  ┆ nebulizer to a   ┆ morning when you ┆ nebulizer is     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ silent portable  ┆ can't breathe or ┆ superior to      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ nebulizer.       ┆ your little one  ┆ loud, bulky      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆ can't breathe.   ┆ hospital-grade   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ units for home   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ emergency use.   │
│ 75811641990453199 ┆ storyboard-v1  ┆ 2        ┆ 3.8     ┆ 8.3   ┆ medium close-up ┆ The woman shows a ┆ Comparing a      ┆ Okay, so I work  ┆ An urgent care   ┆ I'm gonna link   ┆ An urgent care   │
│ 67                ┆                ┆          ┆         ┆       ┆                 ┆ standard urgent   ┆ plug-in,         ┆ in urgent care,  ┆ physician        ┆ this down below  ┆ healthcare       │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ care plug-in      ┆ hospital grade   ┆ and this is the  ┆ assistant        ┆ because this is  ┆ provider         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ nebulizer unit    ┆ nebulizer vs     ┆ one that we use  ┆ compares a       ┆ something that   ┆ demonstrates why │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ sitting on an     ┆ portable         ┆ in our urgent    ┆ noisy,           ┆ you're gonna     ┆ a quiet,         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ examination room  ┆ nebulizer        ┆ care setting.    ┆ traditional      ┆ wanna have at 2  ┆ rechargeable     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ counter.          ┆                  ┆                  ┆ hospital         ┆ o'clock in the   ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ nebulizer to a   ┆ morning when you ┆ nebulizer is     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ silent portable  ┆ can't breathe or ┆ superior to      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ nebulizer.       ┆ your little one  ┆ loud, bulky      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆ can't breathe.   ┆ hospital-grade   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ units for home   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ emergency use.   │
│ 75811641990453199 ┆ storyboard-v1  ┆ 3        ┆ 8.3     ┆ 17.5  ┆ close-up        ┆ She turns on the  ┆ Comparing a      ┆ I want you to    ┆ An urgent care   ┆ I'm gonna link   ┆ An urgent care   │
│ 67                ┆                ┆          ┆         ┆       ┆                 ┆ hospital          ┆ plug-in,         ┆ listen to it...  ┆ physician        ┆ this down below  ┆ healthcare       │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ nebulizer,        ┆ hospital grade   ┆ how loud it is.  ┆ assistant        ┆ because this is  ┆ provider         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ demonstrating its ┆ nebulizer vs     ┆ Okay, so you see ┆ compares a       ┆ something that   ┆ demonstrates why │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ noisy motor and   ┆ portable         ┆ that continuous  ┆ noisy,           ┆ you're gonna     ┆ a quiet,         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ constant vapor    ┆ nebulizer        ┆ stream, right?   ┆ traditional      ┆ wanna have at 2  ┆ rechargeable     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ steam.            ┆                  ┆ Okay, now I'm    ┆ hospital         ┆ o'clock in the   ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ gonna turn it    ┆ nebulizer to a   ┆ morning when you ┆ nebulizer is     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ off...           ┆ silent portable  ┆ can't breathe or ┆ superior to      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ nebulizer.       ┆ your little one  ┆ loud, bulky      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆ can't breathe.   ┆ hospital-grade   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ units for home   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ emergency use.   │
│ 75811641990453199 ┆ storyboard-v1  ┆ 4        ┆ 17.5    ┆ 28.5  ┆ close-up        ┆ She activates the ┆                  ┆ ...and I want    ┆ An urgent care   ┆ I'm gonna link   ┆ An urgent care   │
│ 67                ┆                ┆          ┆         ┆       ┆                 ┆ portable          ┆                  ┆ you to see this  ┆ physician        ┆ this down below  ┆ healthcare       │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ nebulizer,        ┆                  ┆ portable         ┆ assistant        ┆ because this is  ┆ provider         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ pointing out its  ┆                  ┆ nebulizer, and   ┆ compares a       ┆ something that   ┆ demonstrates why │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ LED digital       ┆                  ┆ look at the      ┆ noisy,           ┆ you're gonna     ┆ a quiet,         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ display screen    ┆                  ┆ stream on there. ┆ traditional      ┆ wanna have at 2  ┆ rechargeable     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ and multiple      ┆                  ┆ It's got 3       ┆ hospital         ┆ o'clock in the   ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ misting speed     ┆                  ┆ modes:           ┆ nebulizer to a   ┆ morning when you ┆ nebulizer is     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ modes.            ┆                  ┆ continuous, 5    ┆ silent portable  ┆ can't breathe or ┆ superior to      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ minutes of       ┆ nebulizer.       ┆ your little one  ┆ loud, bulky      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ gentle, and then ┆                  ┆ can't breathe.   ┆ hospital-grade   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ it's got 20      ┆                  ┆                  ┆ units for home   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ minutes of this  ┆                  ┆                  ┆ emergency use.   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ pulsation mode.  ┆                  ┆                  ┆                  │
│ 75811641990453199 ┆ storyboard-v1  ┆ 5        ┆ 28.5    ┆ 35.0  ┆ close-up        ┆ She turns the     ┆                  ┆ This is          ┆ An urgent care   ┆ I'm gonna link   ┆ An urgent care   │
│ 67                ┆                ┆          ┆         ┆       ┆                 ┆ handheld unit     ┆                  ┆ rechargeable in  ┆ physician        ┆ this down below  ┆ healthcare       │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ around to show    ┆                  ┆ the back. It's   ┆ assistant        ┆ because this is  ┆ provider         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ the charging port ┆                  ┆ got anti-leak    ┆ compares a       ┆ something that   ┆ demonstrates why │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ on the back and   ┆                  ┆ top, so you can  ┆ noisy,           ┆ you're gonna     ┆ a quiet,         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ opens the         ┆                  ┆ put your         ┆ traditional      ┆ wanna have at 2  ┆ rechargeable     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ anti-leak         ┆                  ┆ medicine in      ┆ hospital         ┆ o'clock in the   ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ medication cup    ┆                  ┆ here...          ┆ nebulizer to a   ┆ morning when you ┆ nebulizer is     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ top.              ┆                  ┆                  ┆ silent portable  ┆ can't breathe or ┆ superior to      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ nebulizer.       ┆ your little one  ┆ loud, bulky      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆ can't breathe.   ┆ hospital-grade   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ units for home   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ emergency use.   │
│ 75811641990453199 ┆ storyboard-v1  ┆ 6        ┆ 35.0    ┆ 43.0  ┆ medium close-up ┆ She turns both    ┆                  ┆ ...but look,     ┆ An urgent care   ┆ I'm gonna link   ┆ An urgent care   │
│ 67                ┆                ┆          ┆         ┆       ┆                 ┆ nebulizers on     ┆                  ┆ this is          ┆ physician        ┆ this down below  ┆ healthcare       │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ side-by-side to   ┆                  ┆ comparison. I    ┆ assistant        ┆ because this is  ┆ provider         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ highlight the     ┆                  ┆ wanna show you   ┆ compares a       ┆ something that   ┆ demonstrates why │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ sound difference  ┆                  ┆ comparison. So   ┆ noisy,           ┆ you're gonna     ┆ a quiet,         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ and mist density. ┆                  ┆ there's that...  ┆ traditional      ┆ wanna have at 2  ┆ rechargeable     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ hospital         ┆ o'clock in the   ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ nebulizer to a   ┆ morning when you ┆ nebulizer is     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ silent portable  ┆ can't breathe or ┆ superior to      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ nebulizer.       ┆ your little one  ┆ loud, bulky      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆ can't breathe.   ┆ hospital-grade   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ units for home   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ emergency use.   │
│ 75811641990453199 ┆ storyboard-v1  ┆ 7        ┆ 43.0    ┆ 54.5  ┆ talking-head    ┆ She holds up both ┆                  ┆ ...hospital      ┆ An urgent care   ┆ I'm gonna link   ┆ An urgent care   │
│ 67                ┆                ┆          ┆         ┆       ┆                 ┆ units while       ┆                  ┆ grade, portable  ┆ physician        ┆ this down below  ┆ healthcare       │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ talking directly  ┆                  ┆ that you can     ┆ assistant        ┆ because this is  ┆ provider         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ to the viewer     ┆                  ┆ purchase off of  ┆ compares a       ┆ something that   ┆ demonstrates why │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ about the         ┆                  ┆ TikTok Shop. I'm ┆ noisy,           ┆ you're gonna     ┆ a quiet,         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ importance of     ┆                  ┆ gonna link this  ┆ traditional      ┆ wanna have at 2  ┆ rechargeable     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ having a quiet    ┆                  ┆ down below       ┆ hospital         ┆ o'clock in the   ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ nebulizer for     ┆                  ┆ because this is  ┆ nebulizer to a   ┆ morning when you ┆ nebulizer is     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ late-night asthma ┆                  ┆ something that   ┆ silent portable  ┆ can't breathe or ┆ superior to      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ or respiratory    ┆                  ┆ you're gonna     ┆ nebulizer.       ┆ your little one  ┆ loud, bulky      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ emergencies.      ┆                  ┆ wanna have at 2  ┆                  ┆ can't breathe.   ┆ hospital-grade   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ o'clock in the   ┆                  ┆                  ┆ units for home   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ morning when you ┆                  ┆                  ┆ emergency use.   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ can't b…         ┆                  ┆                  ┆                  │
│ 75811641990453199 ┆ storyboard-v1  ┆ 8        ┆ 54.5    ┆ 102.7 ┆ close-up        ┆ She demonstrates  ┆                  ┆ ...it comes with ┆ An urgent care   ┆ I'm gonna link   ┆ An urgent care   │
│ 67                ┆                ┆          ┆         ┆       ┆                 ┆ the included      ┆                  ┆ three different  ┆ physician        ┆ this down below  ┆ healthcare       │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ attachments       ┆                  ┆ pieces: you've   ┆ assistant        ┆ because this is  ┆ provider         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ including the     ┆                  ┆ got your         ┆ compares a       ┆ something that   ┆ demonstrates why │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ mouthpiece,       ┆                  ┆ mouthpiece here, ┆ noisy,           ┆ you're gonna     ┆ a quiet,         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ pediatric mask,   ┆                  ┆ you got a        ┆ traditional      ┆ wanna have at 2  ┆ rechargeable     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ and adult mask.   ┆                  ┆ pediatric mask,  ┆ hospital         ┆ o'clock in the   ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ and an adult     ┆ nebulizer to a   ┆ morning when you ┆ nebulizer is     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ mask. This is    ┆ silent portable  ┆ can't breathe or ┆ superior to      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆ fantastic!       ┆ nebulizer.       ┆ your little one  ┆ loud, bulky      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆ can't breathe.   ┆ hospital-grade   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ units for home   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ emergency use.   │
│ 76699887120333734 ┆ storyboard-v1  ┆ 1        ┆ 0.0     ┆ 4.0   ┆ close-up        ┆ A baby sleeps     ┆ Huge thank you   ┆                  ┆ A text hook      ┆                  ┆ This video       │
│ 71                ┆                ┆          ┆         ┆       ┆                 ┆ peacefully on a   ┆ to The nurse who ┆                  ┆ thanking a nurse ┆                  ┆ highlights a     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ mother's lap      ┆ said to Get this ┆                  ┆ for recommending ┆                  ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ while the mother  ┆ before cold and  ┆                  ┆ a portable       ┆                  ┆ handheld         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ holds a silent    ┆ flu season       ┆                  ┆ nebulizer before ┆                  ┆ nebulizer as a   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ portable          ┆                  ┆                  ┆ cold and flu     ┆                  ┆ nurse-recommende │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ nebulizer near    ┆                  ┆                  ┆ season while     ┆                  ┆ d must-have      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ the baby's face.  ┆                  ┆                  ┆ showing a baby   ┆                  ┆ product for      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ sleeping         ┆                  ┆ infants during   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ undisturbed.     ┆                  ┆ cold and flu     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ season.          │
│ 76699887120333734 ┆ storyboard-v1  ┆ 2        ┆ 4.0     ┆ 7.0   ┆ medium shot     ┆ The mother turns  ┆ Huge thank you   ┆                  ┆ A text hook      ┆                  ┆ This video       │
│ 71                ┆                ┆          ┆         ┆       ┆                 ┆ on the portable   ┆ to The nurse who ┆                  ┆ thanking a nurse ┆                  ┆ highlights a     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ nebulizer,        ┆ said to Get this ┆                  ┆ for recommending ┆                  ┆ portable         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ releasing a       ┆ before cold and  ┆                  ┆ a portable       ┆                  ┆ handheld         │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ stream of fine    ┆ flu season       ┆                  ┆ nebulizer before ┆                  ┆ nebulizer as a   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ mist without      ┆                  ┆                  ┆ cold and flu     ┆                  ┆ nurse-recommende │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ waking the        ┆                  ┆                  ┆ season while     ┆                  ┆ d must-have      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆ sleeping baby.    ┆                  ┆                  ┆ showing a baby   ┆                  ┆ product for      │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ sleeping         ┆                  ┆ infants during   │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆ undisturbed.     ┆                  ┆ cold and flu     │
│                   ┆                ┆          ┆         ┆       ┆                 ┆                   ┆                  ┆                  ┆                  ┆                  ┆ season.          │
└───────────────────┴────────────────┴──────────┴─────────┴───────┴─────────────────┴───────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```