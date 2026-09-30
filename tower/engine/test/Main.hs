module Main where

import Control.Monad (unless)
import Data.List (find, isPrefixOf, sort)
import Metonymy.Contextual
import Metonymy.ContextualChecked
import Metonymy.ContextSpec
import Metonymy.Cathedrals
import Metonymy.Eswatini
import Metonymy.FleetStreet
import Metonymy.Rijeka
import Metonymy.Busan
import Metonymy.AuthorWork
import Metonymy.PartWhole
import Metonymy.CauseEffect
import Metonymy.MaterialObject
import Metonymy.ContainerContent
import Metonymy.Elaborator
import Metonymy.GF
import Metonymy.MoldeFK
import Metonymy.Snapshot
import Metonymy.SyntheticTowers
import Metonymy.Types
import Metonymy.Waterloo
import System.Exit (exitFailure)

main :: IO ()
main = do
  (waterlooSnapshot, waterlooRules) <-
    loadSnapshot "tower/data/wikidata-qid-snapshot"
  waterlooAliases <- loadSnapshotAliases "tower/data/wikidata-qid-snapshot"
  (syntheticTowersSnapshot, _) <-
    loadSnapshot "tower/data/synthetic-towers-snapshot"
  (containerSnapshot, _) <-
    loadSnapshot "tower/data/container-content-snapshot"
  loadedContextScenarios <-
    loadContextScenarios waterlooSnapshot "tower/data/contextual-scenarios.tsv"
  let waterlooContext = waterlooContextFor waterlooSnapshot
      moldeContext = moldeContextFor waterlooSnapshot

  -- spaceBeforeCommas (Metonymy/GF.hs): confirmed by direct testing
  -- against a real gf.exe build (the official Windows release of GF
  -- 3.12, against this project's own pinned gf-rgl commit) that GF's
  -- default whitespace-only tokenizer treats "word," as one indivisible
  -- token, and no grammar-level device (BIND/SOFT_BIND included) can
  -- split it back apart at parse time -- every comma-using construct in
  -- grammar/MetonymyEng.gf (BecauseS/SBecauseS-family,
  -- ApposCommaPN1/ApposCommaPN2) needs the comma to already be its own
  -- token by the time it reaches GF's parser, exactly like real English
  -- commas already are whenever they happen to be preceded by a space.
  assert
    "spaceBeforeCommas inserts a space before a comma that lacks one"
    (spaceBeforeCommas "Waterloo, Ontario" == "Waterloo , Ontario")
  assert
    "spaceBeforeCommas is a no-op when a space already precedes the comma"
    (spaceBeforeCommas "Waterloo , Ontario" == "Waterloo , Ontario")
  assert
    "spaceBeforeCommas handles multiple commas in one sentence"
    ( spaceBeforeCommas "Because X, Y announces Z, W"
        == "Because X , Y announces Z , W"
    )
  assert
    "spaceBeforeCommas is a no-op on a sentence with no comma at all"
    (spaceBeforeCommas "Waterloo announces a programme" == "Waterloo announces a programme")
  assert
    "spaceBeforeCommas handles a comma as the very first character"
    (spaceBeforeCommas ",Waterloo" == ",Waterloo")

  -- spaceAroundParens (Metonymy/GF.hs): same tokenizer limitation as
  -- spaceBeforeCommas, confirmed the same way (a real local gf.exe
  -- build) -- "(HOLA)" with no spacing is one indivisible token that an
  -- unrelated existing rule (OpenPN3) silently absorbed instead of
  -- grammar/Metonymy.gf's own ParenNP ever matching it.
  assert
    "spaceAroundParens inserts a space before an unspaced opening paren"
    (spaceAroundParens "Foundation(HOLA)" == "Foundation (HOLA)")
  assert
    "spaceAroundParens inserts a space after an unspaced closing paren"
    (spaceAroundParens "(HOLA)based" == "(HOLA) based")
  assert
    "spaceAroundParens is a no-op when both sides are already spaced"
    (spaceAroundParens "Foundation ( HOLA ) based" == "Foundation ( HOLA ) based")
  assert
    "spaceAroundParens is a no-op on a sentence with no parens at all"
    (spaceAroundParens "Waterloo announces a programme" == "Waterloo announces a programme")

  assert
    "Waterloo tree elaborates with ordered lexical origins"
    ( case
        elaborateContext
          (snapshotHash waterlooSnapshot)
          (contextSource waterlooContext)
          "announce"
          SubjectHole
          waterlooTree of
        Right context ->
          map
            (\constraint -> (constraintOrigin constraint, constraintPayload constraint))
            (contextConstraints context)
            == map
              (\constraint -> (constraintOrigin constraint, constraintPayload constraint))
              (contextConstraints waterlooContext)
        Left _ -> False
    )
  assert
    "unsupported lexical construction fails closed"
    ( case
        elaborateContext
          (snapshotHash waterlooSnapshot)
          (contextSource waterlooContext)
          "announce"
          SubjectHole
          (LexicalApply "UnsupportedGFNode" []) of
        Left (UnsupportedConstruction _) -> True
        _ -> False
    )
  assert
    "GF application tree is lexicalized with concrete source spans"
    ( case
        lexicalizeGFTree
          "Waterloo announced programme"
          [ LexicalBinding "WaterlooGF" "waterloo" "Waterloo" []
          , LexicalBinding
              "AnnounceGF"
              "announce"
              "announced"
              [Requires (AnyOf [HasSort Animate, HasSort Organization])]
          , LexicalBinding "ProgrammeGF" "programme" "programme" []
          ]
          "Pred WaterlooGF (Compl AnnounceGF ProgrammeGF)" of
        Right tree ->
          case
              elaborateContext
                (snapshotHash waterlooSnapshot)
                (EntityId "Q639408")
                "announce"
                SubjectHole
                tree of
            Right context ->
              map
                (anchorStart . constraintOrigin)
                (contextConstraints context)
                == [9]
            Left _ -> False
        Left _ -> False
    )
  assert
    "GF quantified lexical constructor retains its noun and span"
    ( case
        lexicalizeGFTree
          "every student reads Tolstoy"
          [ LexicalBinding
              "EveryCN"
              "student"
              "student"
              [Requires (HasSort Human)]
          , LexicalBinding "Read" "read" "reads" []
          , LexicalBinding "Tolstoy" "tolstoy" "Tolstoy" []
          ]
          "Pred (EveryCN \"student\" \"students\") (Compl Read Tolstoy)" of
        Right tree ->
          case
              elaborateContext
                (snapshotHash waterlooSnapshot)
                (EntityId "Q639408")
                "read"
                SubjectHole
                tree of
            Right context ->
              case contextConstraints context of
                [constraint] ->
                  anchorStart (constraintOrigin constraint) == 6
                    && anchorSurface (constraintOrigin constraint) == "student"
                _ -> False
            Left _ -> False
        Left _ -> False
    )
  assert
    "snapshot rules include inverse institution projection"
    ( any
        ( \projection ->
            projectionRelation projection == InstitutionOf
              && projectionInverse projection
        )
        (relationProjections waterlooRules)
    )
  assert
    "snapshot alias layer resolves Waterloo to its QID"
    (lookup "Waterloo" waterlooAliases == Just (EntityId "Q639408"))
  assert
    "contextual scenario file has the expected number of rows"
    (length loadedContextScenarios == 72)
  assert
    "Waterloo contextual scenario is loaded from versioned data"
    ( case find ((== "waterloo") . contextScenarioName) loadedContextScenarios of
        Just scenario ->
          contextSource (contextScenarioContext scenario) == contextSource waterlooContext
            && contextAction (contextScenarioContext scenario) == contextAction waterlooContext
            && contextConstraints (contextScenarioContext scenario) == contextConstraints waterlooContext
        Nothing -> False
    )
  assert
    "Molde contextual scenario is loaded from versioned data"
    ( case find ((== "molde") . contextScenarioName) loadedContextScenarios of
        Just scenario ->
          contextSource (contextScenarioContext scenario) == contextSource moldeContext
            && contextAction (contextScenarioContext scenario) == contextAction moldeContext
            && contextConstraints (contextScenarioContext scenario) == contextConstraints moldeContext
        Nothing -> False
    )

  -- Six real, single-signal WiMCor University-of-X examples, loaded
  -- straight from data/contextual-scenarios.tsv rather than individual
  -- Haskell modules -- the scale tier: minimal curated snapshot (the one
  -- real InstitutionOf edge each, no per-city decoy search the way
  -- Molde/Rijeka got), so uniqueness here reflects that curation choice,
  -- not a claim that no other organization exists in that city on real
  -- Wikidata. Two of the six needed their real P31 values registered as
  -- University (Q875538 "public university", Q38723 "higher education
  -- institution") rather than assuming Q3918 -- checked via live
  -- wbgetentities, not assumed uniform across all six.
  mapM_
    ( \(name, university) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real university, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [university])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("houston-university", "Q1472358")
    , ("exeter-university", "Q1414861")
    , ("rochester-university", "Q149990")
    , ("durham-university", "Q458393")
    , ("bath-university", "Q1422458")
    , ("derby-university", "Q3183295")
    ]

  -- Scale batch 2: six more real WiMCor TEAM examples (city -> football
  -- club), same lighter, no-decoy-search tier as the university batch
  -- above. Two of the six needed their real P31 registered (Q51481377
  -- "women's association football club" for Portland Thorns FC,
  -- Q103229495 "men's association football team" for FC Barcelona)
  -- rather than assuming the usual Q476028.
  mapM_
    ( \(name, club) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real club, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [club])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("zagreb-team", "Q462411")
    , ("cluj-team", "Q205998")
    , ("portland-team", "Q1446672")
    , ("barcelona-team", "Q7156")
    , ("lyon-team", "Q704")
    , ("casablanca-team", "Q1051514")
    ]

  -- Scale batch 3: five real WiMCor ARTIFACT examples, same lighter,
  -- no-decoy-search tier. Each needed its own real P31 type registered
  -- (national park, English country house, horse racing venue, the
  -- Spanish heritage term "Real Sitio", theatre building) -- none of
  -- these five real entities happened to share a P31 value with each
  -- other or with Gloucester/Ely Cathedral's Q56242250, checked
  -- individually rather than assumed. Two other real WiMCor ARTIFACT
  -- candidates (Doncaster Racecourse, Ibrox Stadium) were dropped after
  -- checking: Doncaster has no P131 claim at all, and Ibrox's P131 is
  -- Glasgow (the neighbourhood, not the WiMCor surface).
  mapM_
    ( \(name, artifact) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real artifact, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [artifact])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("banff-artifact", "Q41858")
    , ("highclere-artifact", "Q1508450")
    , ("epsom-artifact", "Q5383997")
    , ("elescorial-artifact", "Q9067094")
    , ("chichester-artifact", "Q5095994")
    ]

  -- Scale batch 5: five more real WiMCor University-of-X examples,
  -- same lighter tier. Of eleven candidates checked this round (six here
  -- plus five more not kept), only five matched: Monmouth (P131 is
  -- Illinois, the state), Webster (P131 is "Webster Groves", not exactly
  -- "Webster"), Azusa (P131 is California, the state), Kyoto (P131 is
  -- Sakyo-ku, a ward), and George Mason (the WiMCor surface is the
  -- university's own name, not a place at all) were all dropped as real
  -- mismatches or miscategorized candidates, not forced through.
  mapM_
    ( \(name, university) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real university, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [university])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("birmingham-university", "Q1472663")
    , ("pisa-university", "Q645663")
    , ("guadalajara-university", "Q164028")
    , ("aberystwyth-university", "Q319761")
    , ("standrews-university", "Q216273")
    ]

  -- Scale batch 6: six more real WiMCor TEAM examples, same lighter
  -- tier. All six real P31 values were already Q476028, so no new type
  -- registration was needed this round.
  mapM_
    ( \(name, club) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real club, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [club])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("laspalmas-team", "Q11979")
    , ("helsingborg-team", "Q207503")
    , ("sedan-team", "Q608988")
    , ("odense-team", "Q211912")
    , ("shimizu-team", "Q823384")
    , ("bandung-team", "Q1630834")
    ]

  -- Scale batch 8: five more real WiMCor University-of-X examples. Two
  -- speculative candidates (Reading, Belfast) were checked and dropped
  -- during this round for a different reason than the usual P131
  -- mismatch: neither one actually came from the real WiMCor mining this
  -- session did earlier (subject-candidates.txt) -- they were picked by
  -- general knowledge, not found in the corpus, so kept out to hold the
  -- same real-corpus-attested discipline as every other scale-batch
  -- example.
  mapM_
    ( \(name, university) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real university, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [university])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("wellesley-university", "Q49205")
    , ("freiburg-university", "Q153987")
    , ("boston-university", "Q49110")
    , ("york-university", "Q967165")
    , ("brighton-university", "Q3056813")
    ]

  -- Scale batch 9: seven more real WiMCor TEAM examples, mined fresh
  -- from the full corpus (the original subject-candidates.txt list from
  -- earlier in this session was exhausted by batch 6). All seven real
  -- P31 values were already Q476028, and all seven checked candidates
  -- matched their real P159 target on the first pass.
  mapM_
    ( \(name, club) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real club, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [club])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("dortmund-team", "Q41420")
    , ("toulouse-team", "Q19518")
    , ("porto-team", "Q128446")
    , ("milan-team", "Q1543")
    , ("toronto-team", "Q327238")
    , ("krasnodar-team", "Q220854")
    , ("groningen-team", "Q24711")
    ]

  -- Scale batch 10: four more real WiMCor ARTIFACT examples. Thirteen
  -- fresh candidates were checked this round; only these four matched
  -- their real P131 target (Bangor Cathedral, Blackfriars Theatre,
  -- Denali, Everglades, Aberdeen Proving Ground, Acadia, Darlington
  -- Raceway, Deepdale, and Battersea Power Station were all real
  -- mismatches -- the WiMCor surface names a neighbourhood, borough, or
  -- state that is not the artifact's own real P131 target). All three of
  -- Leeds Castle/Ascot Racecourse/Hackney Empire happened to reuse
  -- already-registered Artifact types from earlier batches (Highclere's
  -- English country house, Epsom's horse racing venue, Chichester's
  -- theatre building); only Campbelltown Stadium needed a new one
  -- (generic "stadium", Q483110).
  mapM_
    ( \(name, artifact) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real artifact, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [artifact])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("leeds-artifact", "Q746876")
    , ("ascot-artifact", "Q723336")
    , ("hackney-artifact", "Q5637363")
    , ("campbelltown-artifact", "Q5028227")
    ]

  -- Scale batch 12: five more real WiMCor TEAM examples, mined with a
  -- wider verb net (finished/beat/relegated/etc., not just announce/
  -- sign) since the earlier lists were exhausted. Viborg, Lugo, Thun,
  -- Morelia, Sabadell. One candidate (Castleford Tigers, a rugby league
  -- club) was checked and dropped: its real P131 is Wakefield, not
  -- Castleford.
  mapM_
    ( \(name, club) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real club, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [club])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("viborg-team", "Q837956")
    , ("lugo-team", "Q11984")
    , ("thun-team", "Q464775")
    , ("morelia-team", "Q1480985")
    , ("sabadell-team", "Q12260")
    ]

  -- Scale batch 14 (final batch of this round): nine more real WiMCor
  -- University-of-X examples, closing this scale-up out at exactly 80
  -- lighter-tier examples on top of the 20 flagship ones (100 total).
  -- Ten candidates were checked; only Oakland University was dropped
  -- (its real P131 targets -- Rochester Hills, Auburn Hills, Oakland
  -- County, Michigan -- are all real places in Michigan, but none is
  -- literally "Oakland"). Utrecht and Heidelberg both rely solely on
  -- Q62078547 ("public research university"), now also registered as
  -- University alongside its existing Organization registration.
  mapM_
    ( \(name, university) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real university, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [university])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("dundee-university", "Q1249005")
    , ("utrecht-university", "Q221653")
    , ("glasgow-university", "Q192775")
    , ("delft-university", "Q752663")
    , ("liverpool-university", "Q499510")
    , ("heidelberg-university", "Q151510")
    , ("salamanca-university", "Q308963")
    , ("auburn-university", "Q540672")
    , ("denver-university", "Q519427")
    ]

  -- Diversity pass 1: ten ObjectHole variants of already-verified
  -- University-of-X places ("he attends X", new Attend V2, verified
  -- against the local gf.exe/pinned gf-rgl build first), reusing the
  -- same real QIDs -- the resolution mechanism does not consult
  -- contextRole at all, so this specifically tests hole-role diversity
  -- (every scale-tier example so far was SubjectHole) rather than
  -- re-verifying anything about the underlying graph.
  mapM_
    ( \(name, university) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " (ObjectHole) contracts uniquely to its real university, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [university])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("houston-attend", "Q1472358")
    , ("exeter-attend", "Q1414861")
    , ("rochester-attend", "Q149990")
    , ("pisa-attend", "Q645663")
    , ("guadalajara-attend", "Q164028")
    , ("wellesley-attend", "Q49205")
    , ("york-attend", "Q967165")
    , ("dundee-attend", "Q1249005")
    , ("glasgow-attend", "Q192775")
    , ("denver-attend", "Q519427")
    ]

  -- Diversity pass 2: two real-verb variants (offer/publish, new V2s,
  -- verified against the local gf.exe/pinned gf-rgl build) instead of
  -- the uniform "has a campus" template -- each grounded in the actual
  -- real WiMCor sentence for that place ("Aber offers a degree scheme",
  -- "David Jesson of York published a series of annual studies"), not
  -- just reapplied to more places without that backing.
  mapM_
    ( \(name, university) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real university, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [university])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("aberystwyth-offer", "Q319761")
    , ("york-publish", "Q967165")
    ]

  assert
    "tower rejects a context bound to another snapshot"
    ( contextualFiber
        waterlooSnapshot
        [InstitutionOf]
        1
        (waterlooContext {contextSnapshotHash = "forged"})
        == Left "snapshot-hash-mismatch"
    )

  case
      contextualFiber
        waterlooSnapshot
        [InstitutionOf]
        1
        waterlooContext of
    Left errorMessage -> do
      putStrLn ("FAIL: Waterloo contextual fiber: " <> errorMessage)
      exitFailure
    Right stages -> do
      assert "Waterloo fiber has one initial and two lexical stages" (length stages == 3)
      assert
        "Waterloo graph layer preserves all institution candidates"
        ( stageTargets (stages !! 0)
            == map EntityId ["Q1049470", "Q2004561", "Q7974219"]
        )
      assert
        "announce layer retains organization candidates"
        (stageTargets (stages !! 1) == stageTargets (stages !! 0))
      assert
        "physics layer retains only positively witnessed institutions"
        (stageTargets (stages !! 2) == map EntityId ["Q1049470", "Q2004561"])
      assert
        "contextual fiber is monotonically restricted"
        ( all
            (`elem` stageTargets (stages !! 0))
            (stageTargets (stages !! 1))
            && all
              (`elem` stageTargets (stages !! 1))
              (stageTargets (stages !! 2))
        )
      assert
        "Waterloo council has a precise missing-relation obstruction"
        ( case stageObstructions (stages !! 2) of
            [MissingRelation _ candidate Conducts target] ->
              candidate == EntityId "Q7974219" && target == EntityId "Q413"
            _ -> False
        )

  case
      contextualFiberChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        waterlooContext of
    Left errorMessage -> do
      putStrLn ("FAIL: Agda-checked Waterloo fiber: " <> errorMessage)
      exitFailure
    Right stages ->
      assert
        "Agda-checked Waterloo fiber matches the executable tower"
        (stageTargets (stages !! 2) == map EntityId ["Q1049470", "Q2004561"])

  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        waterlooContext
        (EntityId "Q1049470") of
    Left message
      | "unsafe-contextual-contraction-non-singleton-fiber" `isPrefixOf` message ->
          assert "ambiguous Waterloo contraction is rejected" True
    other -> do
      putStrLn ("FAIL: expected unsafe Waterloo contraction, got " <> show other)
      exitFailure

  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        waterlooContext
        (EntityId "Q7974219") of
    Left "explicit-target-not-in-final-fiber" ->
      assert "obstructed Waterloo council cannot contract" True
    other -> do
      putStrLn ("FAIL: expected missing council contraction, got " <> show other)
      exitFailure

  let uniqueWaterlooContext =
        waterlooContext
          { contextConstraints =
              contextConstraints waterlooContext
                <> [ ContextConstraint
                      (LexicalAnchor "Noun" "university" "university" 46 56)
                      (Requires (HasSort University))
                      "test:unique-university"
                   ]
          , contextRuleProvenance =
              contextRuleProvenance waterlooContext
                <> ["test:unique-university"]
          }
  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        uniqueWaterlooContext
        (EntityId "Q1049470") of
    Right result ->
      assert
        "unique Waterloo university fiber contracts to the source place"
        ( contractionSource result == EntityId "Q639408"
            && contractionTarget result == EntityId "Q1049470"
            && contractionSafety result == "unique-contextual-fiber"
        )
    Left errorMessage -> do
      putStrLn ("FAIL: unique Waterloo contraction: " <> errorMessage)
      exitFailure

  -- Real two-hop walk (maxDepth=2), genuinely untested at that depth
  -- until now: Waterloo -InstitutionOf(inverse P131)-> University of
  -- Waterloo -InstitutionOf(inverse P361, newly registered)-> Institute
  -- for Quantum Computing (Q3799227, real P361 "part of" claim, already
  -- P31=Q31855 ResearchInstitution -- the same QID already registered
  -- from Perimeter Institute). Reuses InstitutionOf rather than the
  -- existing AffiliatedWith projection: P361/P749's own AffiliatedWith
  -- registration is forward (keeps the claim's own child->parent
  -- direction, IQC->UWaterloo), the opposite of what a source->target
  -- graph walk here needs (UWaterloo->IQC) -- caught by a real CI
  -- failure on the first attempt, not assumed correct in advance. The
  -- initial graph layer at depth 2 finds this fourth, more-distant real
  -- candidate that depth 1 cannot reach; the existing physics/Conducts
  -- constraint still correctly excludes it in the end (it has no P101
  -- claim at all), so going deeper finds more raw candidates without
  -- losing precision.
  case
      contextualFiberChecked
        waterlooSnapshot
        [InstitutionOf]
        2
        waterlooContext of
    Left errorMessage -> do
      putStrLn ("FAIL: depth-2 Waterloo fiber: " <> errorMessage)
      exitFailure
    Right stages -> do
      assert
        "depth-2 graph layer reaches the real second-hop candidate that depth 1 cannot"
        ( sort (map unEntityId (stageTargets (stages !! 0)))
            == sort (map unEntityId [EntityId "Q1049470", EntityId "Q2004561", EntityId "Q3799227", EntityId "Q7974219"])
        )
      assert
        "the existing physics constraint still excludes the deeper candidate correctly"
        (stageTargets (last stages) == map EntityId ["Q1049470", "Q2004561"])

  -- Real, three-signal tower: "Molde announced ... signed Kamara on loan
  -- for the ... season" (real WiMCor sentence, live-Wikidata-verified,
  -- see Metonymy.MoldeFK's module docstring). Unlike Waterloo, one
  -- signal (announce) and two signals (announce+season) both stay
  -- genuinely ambiguous between Molde FK and the real decoy Bjørset FK
  -- -- only the third (on loan, RequiresSome PlaysInLeague) narrows to
  -- the single correct candidate.
  case contextualFiber waterlooSnapshot [InstitutionOf] 1 moldeContext of
    Left errorMessage -> do
      putStrLn ("FAIL: Molde contextual fiber: " <> errorMessage)
      exitFailure
    Right stages -> do
      assert
        "Molde fiber has one initial and three constraint stages"
        (length stages == 4)
      assert
        "Molde graph layer finds both real Molde football clubs"
        ( sort (map unEntityId (stageTargets (stages !! 0)))
            == sort (map unEntityId [moldeFK, bjorsetFK])
        )
      assert
        "announce alone does not disambiguate (both are organizations)"
        (sort (map unEntityId (stageTargets (stages !! 1))) == sort (map unEntityId [moldeFK, bjorsetFK]))
      assert
        "season alone does not disambiguate (both are football clubs)"
        (sort (map unEntityId (stageTargets (stages !! 2))) == sort (map unEntityId [moldeFK, bjorsetFK]))
      assert
        "on loan narrows to the one club with a real league claim"
        (map unEntityId (stageTargets (stages !! 3)) == [unEntityId moldeFK])

  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        moldeContext
        moldeFK of
    Right result ->
      assert
        "unique Molde FK fiber contracts to the source place (Agda-checked)"
        ( contractionSource result == moldeSource
            && contractionTarget result == moldeFK
            && contractionSafety result == "unique-contextual-fiber"
        )
    Left errorMessage -> do
      putStrLn ("FAIL: unique Molde FK contraction: " <> errorMessage)
      exitFailure

  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        moldeContext
        bjorsetFK of
    Left message
      | "explicit-target-not-in-final-fiber" `isPrefixOf` message ->
          assert "the real decoy Bjørset FK is correctly rejected" True
    other -> do
      putStrLn ("FAIL: expected Bjørset FK to be rejected, got " <> show other)
      exitFailure

  -- Two real, single-signal location-for-artifact examples: "Gloucester
  -- has a Norman nave..." and "the lady chapel of Ely..." (see
  -- Metonymy.Cathedrals). A live SPARQL check found no real ambiguity
  -- here (unlike Molde): each place has exactly one Q56242250-typed
  -- entity, so one Requires (HasSort Artifact) signal already narrows
  -- to the unique cathedral.
  mapM_
    ( \(label, context, expected) ->
        case
            contextualContractionChecked
              waterlooSnapshot
              [InstitutionOf]
              1
              context
              expected of
          Right result ->
            assert
              (label <> " contracts uniquely to its cathedral (Agda-checked)")
              (contractionTarget result == expected && contractionSafety result == "unique-contextual-fiber")
          Left errorMessage -> do
            putStrLn ("FAIL: " <> label <> ": " <> errorMessage)
            exitFailure
    )
    [ ("Gloucester -> Gloucester Cathedral", gloucesterContext waterlooSnapshot, gloucesterCathedral)
    , ("Ely -> Ely Cathedral", elyContext waterlooSnapshot, elyCathedral)
    ]

  -- Real, single-signal location-for-event example (see Metonymy.Busan):
  -- the WiMCor EVENT medium had by far the fewest usable subject-position
  -- candidates this session (422 rows, almost none subject-position or
  -- reachable by a verb the grammar already had) -- this is the one real
  -- example found and verified in that domain.
  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        (busanContext waterlooSnapshot)
        busanFilmFestival of
    Right result ->
      assert
        "Busan contracts uniquely to its film festival (Agda-checked)"
        (contractionTarget result == busanFilmFestival && contractionSafety result == "unique-contextual-fiber")
    Left errorMessage -> do
      putStrLn ("FAIL: Busan contraction: " <> errorMessage)
      exitFailure

  -- Real Government-domain example: "The cabinet of eSwatini was placed
  -- in quarantine..." (see Metonymy.Eswatini). Requires (HasSort
  -- Government) narrows the real 88-entity P1001 neighborhood down to
  -- the two real cabinet formations on record; unlike Molde, no further
  -- lexical signal in this sentence distinguishes which one (the real
  -- distinguishing fact is a date, not a word), so this stays an honest
  -- two-candidate result, the same shape as Waterloo.
  case contextualFiberChecked waterlooSnapshot [GovernedBy] 1 (eswatiniContext waterlooSnapshot) of
    Right stages -> do
      assert
        "Eswatini's cabinet narrows to the two real cabinet formations, Agda-checked"
        ( sort (map unEntityId (stageTargets (last stages)))
            == sort (map unEntityId [ambroseMandvuloDlaminiCabinet, russellDlaminiCabinet])
        )
      -- Two distinct real cabinet formations, both a Government-sort
      -- reading of "the cabinet of Eswatini": the coarse-reading
      -- compatibility check (Agda-verified, not just proposed) should
      -- accept them.
      assert
        "Eswatini's two cabinets are reported as one Agda-verified coarse reading"
        ( case contextualCoarseReading waterlooSnapshot [GovernedBy] (eswatiniContext waterlooSnapshot) stages of
            Just reading ->
              coarseReadingSort reading == Government
                && sort (map unEntityId (coarseReadingMembers reading))
                  == sort (map unEntityId [ambroseMandvuloDlaminiCabinet, russellDlaminiCabinet])
            Nothing -> False
        )
    Left errorMessage -> do
      putStrLn ("FAIL: Eswatini cabinet fiber: " <> errorMessage)
      exitFailure

  -- Second real TEAM tower (see Metonymy.Rijeka): unlike Molde, no
  -- lexical signal here distinguishes HNK Rijeka from the real decoy NK
  -- Orijent, so this stays an honest two-candidate result too.
  case contextualFiberChecked waterlooSnapshot [InstitutionOf] 1 (rijekaContext waterlooSnapshot) of
    Right stages -> do
      assert
        "Rijeka's season signal narrows to the two real football clubs, Agda-checked"
        ( sort (map unEntityId (stageTargets (last stages)))
            == sort (map unEntityId [hnkRijeka, nkOrijent])
        )
      -- Place-for-team: both clubs are the same kind of thing
      -- (SportsOrganization), reached by the same relation from the
      -- same city -- should be an Agda-verified coarse reading.
      assert
        "Rijeka's two football clubs are reported as one Agda-verified coarse reading"
        ( case contextualCoarseReading waterlooSnapshot [InstitutionOf] (rijekaContext waterlooSnapshot) stages of
            Just reading ->
              coarseReadingSort reading == SportsOrganization
                && sort (map unEntityId (coarseReadingMembers reading))
                  == sort (map unEntityId [hnkRijeka, nkOrijent])
            Nothing -> False
        )
    Left errorMessage -> do
      putStrLn ("FAIL: Rijeka fiber: " <> errorMessage)
      exitFailure

  -- First real, live-Wikidata-verified Author-for-work example (see
  -- Metonymy.AuthorWork): "...he studied the Romantic poet Novalis,
  -- whose Hymns to the Night left a great impression on him" (real
  -- ConMeC METONYMIC/PRODUCER-category sentence). Requires (HasSort
  -- LiteraryWork) on the governing verb "study" walks the real Authored
  -- (inverse P50) bridge from Novalis to his two real, P31-typed
  -- literary works; no further lexical signal in this sentence
  -- distinguishes which one (the real sentence's own disambiguation is
  -- same-sentence coreference to a literally named work, not a
  -- type/relation signal this mechanism can consume), so this stays an
  -- honest two-candidate result, the same shape as Waterloo/Rijeka/
  -- Eswatini.
  case contextualFiberChecked waterlooSnapshot [Authored] 1 (novalisContext waterlooSnapshot) of
    Right stages -> do
      assert
        "Novalis's studied poetry narrows to his two real literary works, Agda-checked"
        ( sort (map unEntityId (stageTargets (last stages)))
            == sort (map unEntityId [hymnsToTheNight, heinrichVonOfterdingen])
        )
      -- Author-for-work: both texts are the same kind of thing
      -- (LiteraryWork), reached by Authored from the same author --
      -- should be an Agda-verified coarse reading ("a work by Novalis").
      assert
        "Novalis's two works are reported as one Agda-verified coarse reading"
        ( case contextualCoarseReading waterlooSnapshot [Authored] (novalisContext waterlooSnapshot) stages of
            Just reading ->
              coarseReadingSort reading == LiteraryWork
                && sort (map unEntityId (coarseReadingMembers reading))
                  == sort (map unEntityId [hymnsToTheNight, heinrichVonOfterdingen])
            Nothing -> False
        )
    Left errorMessage -> do
      putStrLn ("FAIL: Novalis fiber: " <> errorMessage)
      exitFailure

  -- Negative sanity check for contextualCoarseReading's safety property
  -- (see its own docs, and Metonymy.GeneralCoarseCompatibility's
  -- Agda-side universityCouncilNotCompatible): Waterloo's own real data,
  -- with only the "announce" constraint applied (the "in physics" signal
  -- dropped), leaves three genuinely heterogeneous survivors -- a
  -- university, a research institute, a city council -- selected only by
  -- the broad AnyOf [Animate, Organization] requirement. These must
  -- never be reported as one coarse reading, and this is checked here
  -- against the real, running contextualFiberChecked/
  -- contextualCoarseReading pipeline, not only as a standalone Agda fact.
  let waterlooAnnounceOnlyContext =
        waterlooContext
          { contextConstraints = take 1 (contextConstraints waterlooContext)
          , contextRuleProvenance = take 1 (contextRuleProvenance waterlooContext)
          }
  case contextualFiberChecked waterlooSnapshot [InstitutionOf] 1 waterlooAnnounceOnlyContext of
    Right stages -> do
      assert
        "Waterloo's announce-only constraint leaves three heterogeneous real survivors"
        (length (stageTargets (last stages)) == 3)
      assert
        "Three heterogeneous organizations under a broad AnyOf are NOT reported as one coarse reading"
        ( contextualCoarseReading
            waterlooSnapshot
            [InstitutionOf]
            waterlooAnnounceOnlyContext
            stages
            == Nothing
        )
    Left errorMessage -> do
      putStrLn ("FAIL: Waterloo announce-only fiber: " <> errorMessage)
      exitFailure

  -- "Fleet Street ran the story" (see Metonymy.FleetStreet's module
  -- docstring for exactly what kind of example this is -- a
  -- representative sentence for a documented, deliberately
  -- underdetermined collective usage, not a transcribed corpus
  -- sentence). Requires (HasSort Newspaper) narrows to the three real
  -- national newspapers historically headquartered on Fleet Street,
  -- with no further signal in the sentence to distinguish which one --
  -- and, being deliberately generic, none is meant to.
  case contextualFiberChecked waterlooSnapshot [InstitutionOf] 1 (fleetStreetContext waterlooSnapshot) of
    Right stages -> do
      assert
        "Fleet Street's story narrows to the three real national newspapers, Agda-checked"
        ( sort (map unEntityId (stageTargets (last stages)))
            == sort (map unEntityId [dailyExpress, dailyMail, dailyTelegraph])
        )
      -- Three, not two: the same coarse-reading mechanism generalizes
      -- beyond a pairwise check (verifyCompatibilityWithAgda's every
      -- survivor is checked against the first, not just checked in
      -- pairs).
      assert
        "Fleet Street's three newspapers are reported as one Agda-verified coarse reading"
        ( case contextualCoarseReading waterlooSnapshot [InstitutionOf] (fleetStreetContext waterlooSnapshot) stages of
            Just reading ->
              coarseReadingSort reading == Newspaper
                && sort (map unEntityId (coarseReadingMembers reading))
                  == sort (map unEntityId [dailyExpress, dailyMail, dailyTelegraph])
            Nothing -> False
        )
    Left errorMessage -> do
      putStrLn ("FAIL: Fleet Street fiber: " <> errorMessage)
      exitFailure

  -- Three real, corpus-attested container-for-content examples (ConMeC
  -- CONTAINER category -- see Metonymy.ContainerContent's module
  -- docstring). A different transfer mechanism from location-for-
  -- institution: each container has exactly one real content edge, so
  -- the tower narrows to a unique, Agda-checked candidate through the
  -- graph walk alone, with no extra Requires signal needed.
  mapM_
    ( \(label, context, expected) ->
        case contextualFiberChecked containerSnapshot [Contains] 1 context of
          Right stages ->
            assert
              (label <> " narrows to its one real content, Agda-checked")
              (map unEntityId (stageTargets (last stages)) == [unEntityId expected])
          Left errorMessage -> do
            putStrLn ("FAIL: " <> label <> ": " <> errorMessage)
            exitFailure
    )
    [ ("glass -> rum", glassContext containerSnapshot, rumEntity)
    , ("carton -> milk", cartonContext containerSnapshot, milkEntity)
    , ("pack -> beer", packContext containerSnapshot, beerEntity)
    ]

  -- Scale batch 4: four more real ConMeC CONTAINER examples plus one
  -- surfaced earlier this session but not built (extinguisher), all via
  -- the new Empty verb (see Metonymy.ContainerContent's module
  -- docstring for why "drink" does not fit oxygen/shot).
  mapM_
    ( \(label, context, expected) ->
        case contextualFiberChecked containerSnapshot [Contains] 1 context of
          Right stages ->
            assert
              (label <> " narrows to its one real content, Agda-checked")
              (map unEntityId (stageTargets (last stages)) == [unEntityId expected])
          Left errorMessage -> do
            putStrLn ("FAIL: " <> label <> ": " <> errorMessage)
            exitFailure
    )
    [ ("kettle -> water", kettleContext containerSnapshot, waterEntity)
    , ("tank -> oxygen", tankContext containerSnapshot, oxygenEntity)
    , ("canister -> shot", canisterContext containerSnapshot, shotEntity)
    , ("barrel -> wine", barrelContext containerSnapshot, wineEntity)
    , ("extinguisher -> foam", extinguisherContext containerSnapshot, foamEntity)
    , ("syringe -> drug", syringeContext containerSnapshot, drugEntity)
    , ("reservoir -> water", reservoirContext containerSnapshot, waterEntity)
    , ("platter -> food", platterContext containerSnapshot, foodEntity)
    , ("pool -> workers", poolContext containerSnapshot, workersEntity)
    , ("cup -> wine", cupContext containerSnapshot, wineEntity)
    , ("flask -> liquor", flaskContext containerSnapshot, liquorEntity)
    , ("pitcher -> water", pitcherContext containerSnapshot, waterEntity)
    , ("jar -> beer", jarContext containerSnapshot, beerEntity)
    , ("mug -> coffee", mugContext containerSnapshot, coffeeEntity)
    , ("bowl -> soup", bowlContext containerSnapshot, soupEntity)
    , ("hose -> water", hoseContext containerSnapshot, waterEntity)
    , ("bucket -> water", bucketContext containerSnapshot, waterEntity)
    , ("casserole -> lentils", casseroleContext containerSnapshot, lentilsEntity)
    , ("bottle -> wine", bottleContext containerSnapshot, wineEntity)
    , ("cask -> ale", caskContext containerSnapshot, aleEntity)
    , ("container -> liquid", containerContext2 containerSnapshot, liquidEntity)
    , ("pot -> stew", potContext containerSnapshot, stewEntity)
    ]

  case contextualFiberChecked containerSnapshot [Produces] 1 (orchestraContext containerSnapshot) of
    Right stages ->
      assert
        "orchestra -> symphony narrows to its one real product, Agda-checked"
        (map unEntityId (stageTargets (last stages)) == [unEntityId symphonyEntity])
    Left errorMessage -> do
      putStrLn ("FAIL: orchestra -> symphony: " <> errorMessage)
      exitFailure

  -- Scale-tier diversity pass 3 (+4): six real ConMeC PRODUCER
  -- examples, split between "hear" (performers), "read" (writers), and
  -- "criticize" (philosopher) -- see Metonymy.ContainerContent's module
  -- docstring.
  mapM_
    ( \(label, context, expected) ->
        case contextualFiberChecked containerSnapshot [Produces] 1 context of
          Right stages ->
            assert
              (label <> " narrows to its one real product, Agda-checked")
              (map unEntityId (stageTargets (last stages)) == [unEntityId expected])
          Left errorMessage -> do
            putStrLn ("FAIL: " <> label <> ": " <> errorMessage)
            exitFailure
    )
    [ ("pianist -> performance", pianistContext containerSnapshot, performanceEntity)
    , ("band -> music", bandContext containerSnapshot, musicEntity)
    , ("poet -> poems", poetContext containerSnapshot, poemsEntity)
    , ("playwright -> play", playwrightContext containerSnapshot, playEntity)
    , ("journalist -> articles", journalistContext containerSnapshot, articlesEntity)
    , ("philosopher -> theory", philosopherContext containerSnapshot, theoryEntity)
    ]

  -- Real, corpus-attested Part-for-whole (synecdoche) examples (see
  -- Metonymy.PartWhole): flagship "Egyptian artillery shelled the
  -- Israeli bridge over the canal...", plus two more real, historically
  -- distinct sentences (the 2010 Bombardment of Yeonpyeong; a Civil War
  -- battle account). A third distinct transfer mechanism
  -- (AffiliatedWith, not InstitutionOf/GovernedBy or Contains/Produces);
  -- each has exactly one real affiliation edge, so each narrows to a
  -- unique candidate through the graph walk alone.
  mapM_
    ( \(label, context, expected) ->
        case contextualFiberChecked containerSnapshot [AffiliatedWith] 1 context of
          Right stages ->
            assert
              (label <> ", Agda-checked")
              (map unEntityId (stageTargets (last stages)) == [unEntityId expected])
          Left errorMessage -> do
            putStrLn ("FAIL: " <> label <> ": " <> errorMessage)
            exitFailure
    )
    [ ("artillery -> the Egyptian military", artilleryContext containerSnapshot, egyptianMilitary)
    , ("North Korean artillery -> the North Korean military", northKoreanArtilleryContext containerSnapshot, northKoreanMilitary)
    , ("Confederate artillery -> the Confederate States Army", confederateArtilleryContext containerSnapshot, confederateArmy)
    ]

  -- Real, corpus-attested Cause-for-effect examples (see
  -- Metonymy.CauseEffect): flagship "A trumpet is also heard in the
  -- song right after this line is sung", plus three more real
  -- sentences (siren/organ/horn). A fourth distinct transfer mechanism
  -- (Causes, not InstitutionOf/GovernedBy, Contains/Produces, or
  -- AffiliatedWith); each has exactly one real causal edge, so each
  -- narrows to a unique candidate through the graph walk alone.
  mapM_
    ( \(label, context, expected) ->
        case contextualFiberChecked containerSnapshot [Causes] 1 context of
          Right stages ->
            assert
              (label <> ", Agda-checked")
              (map unEntityId (stageTargets (last stages)) == [unEntityId expected])
          Left errorMessage -> do
            putStrLn ("FAIL: " <> label <> ": " <> errorMessage)
            exitFailure
    )
    [ ("trumpet -> the sound of the trumpet", trumpetContext containerSnapshot, trumpetSound)
    , ("siren -> the sound of the siren", sirenContext containerSnapshot, sirenSound)
    , ("organ -> the sound of the organ", organContext containerSnapshot, organSound)
    , ("horn -> the sound of the horn", hornContext containerSnapshot, hornSound)
    ]

  -- First real, corpus-attested Material-for-object example (see
  -- Metonymy.MaterialObject): "...the brass play a citation of the Jazz
  -- tune Topsy" (real ConMeC METONYMIC/CAUSER-category sentence, target
  -- word "brass" -- the material standing for the instrument section
  -- made of it). A fifth distinct transfer mechanism (Represents, not
  -- Causes/InstitutionOf/GovernedBy/Contains/Produces/AffiliatedWith);
  -- exactly one real edge, so this narrows to a unique candidate through
  -- the graph walk alone.
  case contextualFiberChecked containerSnapshot [Represents] 1 (brassContext containerSnapshot) of
    Right stages ->
      assert
        "brass -> the brass section, Agda-checked"
        (map unEntityId (stageTargets (last stages)) == [unEntityId brassSection])
    Left errorMessage -> do
      putStrLn ("FAIL: brass -> brass section: " <> errorMessage)
      exitFailure

  -- Honest reject tests for the three newer, non-location-for-
  -- institution mechanisms (Container, Producer, Government): each
  -- graph only has the one real edge from its own source, so asking the
  -- tower to contract to an entity from a DIFFERENT source's graph is
  -- correctly refused, the same "explicit-target-not-in-final-fiber"
  -- shape already exercised for Bjørset FK and Waterloo City Council.
  mapM_
    ( \(label, snapshot, relations, context, wrongTarget) ->
        case contextualContractionChecked snapshot relations 1 context wrongTarget of
          Left message
            | "explicit-target-not-in-final-fiber" `isPrefixOf` message ->
                assert label True
          other -> do
            putStrLn ("FAIL: " <> label <> ": expected rejection, got " <> show other)
            exitFailure
    )
    [ ( "glass correctly rejects milk (belongs to carton, not glass)"
      , containerSnapshot
      , [Contains]
      , glassContext containerSnapshot
      , milkEntity
      )
    , ( "orchestra correctly rejects rum (belongs to a glass, not the orchestra)"
      , containerSnapshot
      , [Produces]
      , orchestraContext containerSnapshot
      , rumEntity
      )
    , ( "Eswatini's cabinet correctly rejects an unrelated entity (Gloucester Cathedral)"
      , waterlooSnapshot
      , [GovernedBy]
      , eswatiniContext waterlooSnapshot
      , gloucesterCathedral
      )
    , ( "Novalis's studied poetry correctly rejects Novalis himself (the author, not a work)"
      , waterlooSnapshot
      , [Authored]
      , novalisContext waterlooSnapshot
      , novalisSource
      )
    , ( "artillery correctly rejects rum (belongs to a glass, not the artillery)"
      , containerSnapshot
      , [AffiliatedWith]
      , artilleryContext containerSnapshot
      , rumEntity
      )
    , ( "trumpet correctly rejects rum (belongs to a glass, not the trumpet)"
      , containerSnapshot
      , [Causes]
      , trumpetContext containerSnapshot
      , rumEntity
      )
    , ( "brass correctly rejects rum (belongs to a glass, not the brass)"
      , containerSnapshot
      , [Represents]
      , brassContext containerSnapshot
      , rumEntity
      )
    ]

  -- Compositionality: two different transfer mechanisms, drawing on two
  -- different snapshots (Rijeka's location-for-institution via
  -- waterlooSnapshot, "glass" 's container-for-content via
  -- containerSnapshot), each independently and correctly resolved from
  -- ONE real combined sentence: "Rijeka announces a season and he drinks
  -- the glass". Nothing in the tower shares state across a Context
  -- value (each is a pure record), so this mainly documents that two
  -- lexical anchors sitting in the same real sentence text do not
  -- interfere -- but it is the first time two mechanisms have actually
  -- been run from a single shared sentence rather than two unrelated
  -- ones.
  let compositionRijekaContext =
        Context
          { contextTree =
              LexicalApply
                "AndS"
                [ LexicalApply
                    "Pred"
                    [ LexicalLeaf (LexicalAnchor "OpenPN" "rijeka" "Rijeka" 0 6) []
                    , LexicalApply
                        "Compl"
                        [ LexicalLeaf
                            (LexicalAnchor "Verb" "announce" "announces" 7 16)
                            [Requires (AnyOf [HasSort Animate, HasSort Organization])]
                        , LexicalLeaf (LexicalAnchor "Noun" "season" "season" 19 25) []
                        ]
                    ]
                , LexicalApply
                    "Pred"
                    [ LexicalLeaf (LexicalAnchor "HePN" "he" "he" 30 32) []
                    , LexicalApply
                        "Compl"
                        [LexicalLeaf (LexicalAnchor "Verb" "drink" "drinks" 33 39) [], LexicalLeaf (LexicalAnchor "Noun" "glass" "glass" 44 49) []]
                    ]
                ]
          , contextSnapshotHash = snapshotHash waterlooSnapshot
          , contextSource = rijekaSource
          , contextAction = "announce"
          , contextRole = SubjectHole
          , contextConstraints =
              [ ContextConstraint
                  (LexicalAnchor "Verb" "announce" "announces" 7 16)
                  (Requires (AnyOf [HasSort Animate, HasSort Organization]))
                  "VerbNet:say-37.7"
              ]
          , contextRuleProvenance = ["VerbNet:say-37.7"]
          }
      compositionGlassContext =
        Context
          { contextTree =
              LexicalApply
                "AndS"
                [ LexicalApply
                    "Pred"
                    [ LexicalLeaf (LexicalAnchor "OpenPN" "rijeka" "Rijeka" 0 6) []
                    , LexicalApply
                        "Compl"
                        [LexicalLeaf (LexicalAnchor "Verb" "announce" "announces" 7 16) [], LexicalLeaf (LexicalAnchor "Noun" "season" "season" 19 25) []]
                    ]
                , LexicalApply
                    "Pred"
                    [ LexicalLeaf (LexicalAnchor "HePN" "he" "he" 30 32) []
                    , LexicalApply
                        "Compl"
                        [ LexicalLeaf (LexicalAnchor "Verb" "drink" "drinks" 33 39) [Prefers (HasSort Entity)]
                        , LexicalLeaf (LexicalAnchor "Noun" "glass" "glass" 44 49) []
                        ]
                    ]
                ]
          , contextSnapshotHash = snapshotHash containerSnapshot
          , contextSource = glassEntity
          , contextAction = "drink"
          , contextRole = ObjectHole
          , contextConstraints =
              [ ContextConstraint
                  (LexicalAnchor "Verb" "drink" "drinks" 33 39)
                  (Prefers (HasSort Entity))
                  "local:selectional-lexicon"
              ]
          , contextRuleProvenance = ["local:selectional-lexicon"]
          }
  case contextualFiberChecked waterlooSnapshot [InstitutionOf] 1 compositionRijekaContext of
    Right stages ->
      assert
        "composed sentence: Rijeka half still resolves to its two real clubs"
        ( sort (map unEntityId (stageTargets (last stages)))
            == sort (map unEntityId [hnkRijeka, nkOrijent])
        )
    Left errorMessage -> do
      putStrLn ("FAIL: composed Rijeka half: " <> errorMessage)
      exitFailure
  case contextualFiberChecked containerSnapshot [Contains] 1 compositionGlassContext of
    Right stages ->
      assert
        "composed sentence: glass half still resolves to its one real content"
        (map unEntityId (stageTargets (last stages)) == [unEntityId rumEntity])
    Left errorMessage -> do
      putStrLn ("FAIL: composed glass half: " <> errorMessage)
      exitFailure

  mapM_ (assertSyntheticTower syntheticTowersSnapshot) towers

  putStrLn "all tests passed"

assert :: String -> Bool -> IO ()
assert label condition =
  unless condition $ do
    putStrLn ("FAIL: " <> label)
    exitFailure

-- | Runs one fictional tower (data/synthetic-towers-snapshot,
-- Metonymy.SyntheticTowers) through the real Agda-checked contextual
-- pipeline (Metonymy.ContextualChecked), the same functions the real
-- Waterloo tests above exercise. Five assertions, all through the
-- compiled Agda checker where a fiber is actually computed:
--   1/2. each of the tower's two Sorts ALONE is genuinely ambiguous
--        (two survivors) -- so a later unique narrowing is a real
--        conjunction, not one signal that already sufficed alone.
--   3. both Sorts as Prefers (data/contextual-context-triggers.json's
--      actual, shipped strength for all 78 new entries) does NOT narrow
--      the fiber -- Prefers ranks, never filters
--      (Metonymy.Contextual.applyConstraints).
--   4. both Sorts as Requires (an explicitly hypothetical "if
--      individually verified and promoted" variant, not today's
--      dictionary) narrows to exactly the one candidate sharing both
--      Sorts, and Agda-checked contraction reports
--      "unique-contextual-fiber".
--   5. under that same Requires-both context, a candidate with only ONE
--      of the two Sorts is correctly rejected as a contraction target.
assertSyntheticTower :: Snapshot -> TowerFixture -> IO ()
assertSyntheticTower snapshot fixture = do
  assertFiberTargets
    (label <> ": " <> show firstSort <> " alone is ambiguous")
    (towerContextSingle snapshot fixture firstSort)
    [towerBothCandidate fixture, towerFirstOnlyCandidate fixture]

  assertFiberTargets
    (label <> ": " <> show secondSort <> " alone is ambiguous")
    (towerContextSingle snapshot fixture secondSort)
    [towerBothCandidate fixture, towerSecondOnlyCandidate fixture]

  assertFiberTargets
    (label <> ": prefers-both does not narrow (matches shipped dictionary strength)")
    (towerContextPreferring snapshot fixture)
    [ towerBothCandidate fixture
    , towerFirstOnlyCandidate fixture
    , towerSecondOnlyCandidate fixture
    , towerDecoyCandidate fixture
    ]

  case
      contextualContractionChecked
        snapshot
        [InstitutionOf]
        1
        (towerContextRequiring snapshot fixture)
        (towerBothCandidate fixture) of
    Right result ->
      assert
        (label <> ": requires-both narrows uniquely to the shared-sort candidate (Agda-checked)")
        ( contractionSource result == towerSource fixture
            && contractionTarget result == towerBothCandidate fixture
            && contractionSafety result == "unique-contextual-fiber"
        )
    Left errorMessage -> do
      putStrLn ("FAIL: " <> label <> " requires-both unique contraction: " <> errorMessage)
      exitFailure

  case
      contextualContractionChecked
        snapshot
        [InstitutionOf]
        1
        (towerContextRequiring snapshot fixture)
        (towerFirstOnlyCandidate fixture) of
    Left message
      | "explicit-target-not-in-final-fiber" `isPrefixOf` message ->
          assert (label <> ": requires-both correctly rejects a single-sort candidate") True
    other -> do
      putStrLn
        ( "FAIL: "
            <> label
            <> " expected rejection of the single-sort candidate, got "
            <> show other
        )
      exitFailure
  where
    label = towerLabel fixture
    firstSort = towerFirstSort fixture
    secondSort = towerSecondSort fixture

    assertFiberTargets :: String -> Context -> [EntityId] -> IO ()
    assertFiberTargets assertionLabel context expected =
      case contextualFiberChecked snapshot [InstitutionOf] 1 context of
        Right stages ->
          assert
            assertionLabel
            (sortEntityIds (stageTargets (last stages)) == sortEntityIds expected)
        Left errorMessage -> do
          putStrLn ("FAIL: " <> assertionLabel <> ": " <> errorMessage)
          exitFailure

    sortEntityIds :: [EntityId] -> [String]
    sortEntityIds = sort . map unEntityId

