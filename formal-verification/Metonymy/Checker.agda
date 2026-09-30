{-# OPTIONS --safe --without-K --cubical-compatible #-}

module Metonymy.Checker where

open import Agda.Builtin.Bool
open import Agda.Builtin.Equality
open import Agda.Builtin.List
open import Agda.Builtin.Maybe
open import Agda.Builtin.Nat
open import Agda.Builtin.String

infixr 6 _and_

_and_ : Bool → Bool → Bool
true and right = right
false and _ = false

_or_ : Bool → Bool → Bool
true or _ = true
false or right = right

not : Bool → Bool
not true = false
not false = true

stringEqual : String → String → Bool
stringEqual = primStringEquality

any : {A : Set} → (A → Bool) → List A → Bool
any predicate [] = false
any predicate (value ∷ values) =
  predicate value or any predicate values

record TypeFact : Set where
  constructor typeFact
  field
    typeEntity : String
    typeSort   : String

record RelationFact : Set where
  constructor relationFact
  field
    factRelation : String
    factSource   : String
    factTarget   : String

record SubsortRule : Set where
  constructor subsortRule
  field
    ruleSubsort   : String
    ruleSupersort : String

data Requirement : Set where
  hasSort : String → Requirement
  allOf   : List Requirement → Requirement
  anyOf   : List Requirement → Requirement
  notRequirement : Requirement → Requirement

record PredicateFact : Set where
  constructor predicateFact
  field
    factFunction    : String
    factSubjectRequirement : Requirement
    factObjectRequirement  : Requirement
    factStrength    : String
    factProvenance  : String

record LexemeFact : Set where
  constructor lexemeFact
  field
    lexemeFunction : String
    lexemeEntity   : String

record KnowledgeBase : Set where
  constructor knowledgeBase
  field
    typeFacts      : List TypeFact
    relationFacts  : List RelationFact
    subsortRules   : List SubsortRule
    predicateFacts : List PredicateFact
    lexemeFacts    : List LexemeFact

record Edge : Set where
  constructor edge
  field
    edgeRelation : String
    edgeSource   : String
    edgeTarget   : String

data Hole : Set where
  subjectHole : Hole
  objectHole  : Hole

data Direction : Set where
  expand   : Direction
  contract : Direction

record ForgetContext : Set where
  constructor forgetContext
  field
    genericWholeFiber       : Bool
    contextHasRestrictor    : Bool
    contextHasQuantifier    : Bool
    contextIsPositive       : Bool
    contextIsUnfocused      : Bool
    contextHasAnaphor       : Bool
    contextHasTemporal      : Bool

open ForgetContext public

record RawCertificate : Set where
  constructor rawCertificate
  field
    rawDirection  : Direction
    rawForgetContext : ForgetContext
    rawPredicate  : String
    rawHole       : Hole
    rawSource     : String
    rawTarget     : String
    rawRequirement : Requirement
    rawStrength   : String
    rawProvenance : String
    rawEdges      : List Edge

open TypeFact
open RelationFact
open SubsortRule
open PredicateFact
open LexemeFact
open KnowledgeBase
open Edge
open RawCertificate

defaultForgetContext : ForgetContext
defaultForgetContext =
  forgetContext true false false true true false false

forgetContextSafe : ForgetContext → Bool
forgetContextSafe context =
  genericWholeFiber context
    and not (contextHasRestrictor context)
    and not (contextHasQuantifier context)
    and contextIsPositive context
    and contextIsUnfocused context
    and not (contextHasAnaphor context)
    and not (contextHasTemporal context)

directType : KnowledgeBase → String → String → Bool
directType kb entity sort =
  any matches (typeFacts kb)
  where
    matches : TypeFact → Bool
    matches fact =
      stringEqual entity (typeEntity fact)
        and stringEqual sort (typeSort fact)

hasTypeFuel : Nat → KnowledgeBase → String → String → Bool
hasTypeFuel zero kb entity sort = directType kb entity sort
hasTypeFuel (suc fuel) kb entity sort =
  directType kb entity sort
    or any throughRule (subsortRules kb)
  where
    throughRule : SubsortRule → Bool
    throughRule rule =
      stringEqual sort (ruleSupersort rule)
        and hasTypeFuel fuel kb entity (ruleSubsort rule)

hasType : KnowledgeBase → String → String → Bool
hasType = hasTypeFuel 32

mutual
  requirementEqual : Requirement → Requirement → Bool
  requirementEqual (hasSort left) (hasSort right) =
    stringEqual left right
  requirementEqual (allOf left) (allOf right) =
    requirementListEqual left right
  requirementEqual (anyOf left) (anyOf right) =
    requirementListEqual left right
  requirementEqual (notRequirement left) (notRequirement right) =
    requirementEqual left right
  requirementEqual _ _ = false

  requirementListEqual : List Requirement → List Requirement → Bool
  requirementListEqual [] [] = true
  requirementListEqual (left ∷ lefts) (right ∷ rights) =
    requirementEqual left right and requirementListEqual lefts rights
  requirementListEqual _ _ = false

mutual
  satisfiesRequirement :
    KnowledgeBase → String → Requirement → Bool
  satisfiesRequirement kb entity (hasSort sort) =
    hasType kb entity sort
  satisfiesRequirement kb entity (allOf requirements) =
    satisfiesAll kb entity requirements
  satisfiesRequirement kb entity (anyOf requirements) =
    satisfiesAny kb entity requirements
  satisfiesRequirement kb entity (notRequirement requirement) =
    not (satisfiesRequirement kb entity requirement)

  satisfiesAll :
    KnowledgeBase → String → List Requirement → Bool
  satisfiesAll kb entity [] = true
  satisfiesAll kb entity (requirement ∷ requirements) =
    satisfiesRequirement kb entity requirement
      and satisfiesAll kb entity requirements

  satisfiesAny :
    KnowledgeBase → String → List Requirement → Bool
  satisfiesAny kb entity [] = false
  satisfiesAny kb entity (requirement ∷ requirements) =
    satisfiesRequirement kb entity requirement
      or satisfiesAny kb entity requirements

relationExists : KnowledgeBase → Edge → Bool
relationExists kb candidate =
  any matches (relationFacts kb)
  where
    matches : RelationFact → Bool
    matches fact =
      stringEqual (edgeRelation candidate) (factRelation fact)
        and stringEqual (edgeSource candidate) (factSource fact)
        and stringEqual (edgeTarget candidate) (factTarget fact)

nonEmpty : {A : Set} → List A → Bool
nonEmpty [] = false
nonEmpty (_ ∷ _) = true

pathValidFrom :
  KnowledgeBase →
  String →
  String →
  List Edge →
  Bool
pathValidFrom kb current target [] =
  stringEqual current target
pathValidFrom kb current target (candidate ∷ rest) =
  stringEqual current (edgeSource candidate)
    and relationExists kb candidate
    and pathValidFrom kb (edgeTarget candidate) target rest

pathValid : KnowledgeBase → RawCertificate → Bool
pathValid kb raw =
  pathValidFrom
    kb
    (rawSource raw)
    (rawTarget raw)
    (rawEdges raw)

holeRequirement : Hole → PredicateFact → Requirement
holeRequirement subjectHole = factSubjectRequirement
holeRequirement objectHole = factObjectRequirement

predicateValid : KnowledgeBase → RawCertificate → Bool
predicateValid kb raw =
  any matches (predicateFacts kb)
  where
    matches : PredicateFact → Bool
    matches fact =
      stringEqual (rawPredicate raw) (factFunction fact)
        and requirementEqual
          (rawRequirement raw)
          (holeRequirement (rawHole raw) fact)
        and stringEqual (rawStrength raw) (factStrength fact)
        and stringEqual (rawProvenance raw) (factProvenance fact)

isHardRequirement : RawCertificate → Bool
isHardRequirement raw =
  stringEqual (rawStrength raw) "HardRequirement"

isSelectionalPreference : RawCertificate → Bool
isSelectionalPreference raw =
  stringEqual (rawStrength raw) "SelectionalPreference"

check : KnowledgeBase → RawCertificate → Bool
check kb raw =
  nonEmpty (rawEdges raw)
    and predicateValid kb raw
    and pathValid kb raw
    and satisfiesRequirement kb (rawTarget raw) (rawRequirement raw)

andTrueLeft : {left right : Bool} → left and right ≡ true → left ≡ true
andTrueLeft {true} proof = refl
andTrueLeft {false} ()

andTrueRight : {left right : Bool} → left and right ≡ true → right ≡ true
andTrueRight {true} proof = proof
andTrueRight {false} ()

andOfTrue :
  {left right : Bool} →
  left ≡ true →
  right ≡ true →
  left and right ≡ true
andOfTrue refl refl = refl

record Admissible
  (kb : KnowledgeBase)
  (raw : RawCertificate) : Set where
  constructor admissible
  field
    hasEdgesProof :
      nonEmpty (rawEdges raw) ≡ true

    predicateProof :
      predicateValid kb raw ≡ true

    pathProof :
      pathValid kb raw ≡ true

    targetTypeProof :
      satisfiesRequirement kb (rawTarget raw) (rawRequirement raw) ≡ true

checkSound :
  (kb : KnowledgeBase) →
  (raw : RawCertificate) →
  check kb raw ≡ true →
  Admissible kb raw
checkSound kb raw proof =
  admissible
    ( andTrueLeft
        {left = nonEmpty (rawEdges raw)}
        { right =
            predicateValid kb raw
              and pathValid kb raw
              and satisfiesRequirement kb (rawTarget raw) (rawRequirement raw)
        }
        proof
    )
    ( andTrueLeft
        {left = predicateValid kb raw}
        { right =
            pathValid kb raw
              and satisfiesRequirement kb (rawTarget raw) (rawRequirement raw)
        }
        ( andTrueRight
            {left = nonEmpty (rawEdges raw)}
            { right =
                predicateValid kb raw
                  and pathValid kb raw
                  and satisfiesRequirement kb (rawTarget raw) (rawRequirement raw)
            }
            proof
        )
    )
    ( andTrueLeft
        {left = pathValid kb raw}
        { right =
            satisfiesRequirement kb (rawTarget raw) (rawRequirement raw)
        }
        ( andTrueRight
            {left = predicateValid kb raw}
            { right =
                pathValid kb raw
                  and satisfiesRequirement kb (rawTarget raw) (rawRequirement raw)
            }
            ( andTrueRight
                {left = nonEmpty (rawEdges raw)}
                { right =
                    predicateValid kb raw
                      and pathValid kb raw
                      and satisfiesRequirement
                        kb
                        (rawTarget raw)
                        (rawRequirement raw)
                }
                proof
            )
        )
    )
    ( andTrueRight
        {left = pathValid kb raw}
        { right =
            satisfiesRequirement kb (rawTarget raw) (rawRequirement raw)
        }
        ( andTrueRight
            {left = predicateValid kb raw}
            { right =
                pathValid kb raw
                  and satisfiesRequirement kb (rawTarget raw) (rawRequirement raw)
            }
            ( andTrueRight
                {left = nonEmpty (rawEdges raw)}
                { right =
                    predicateValid kb raw
                      and pathValid kb raw
                      and satisfiesRequirement
                        kb
                        (rawTarget raw)
                        (rawRequirement raw)
                }
                proof
            )
        )
    )

checkComplete :
  (kb : KnowledgeBase) →
  (raw : RawCertificate) →
  Admissible kb raw →
  check kb raw ≡ true
checkComplete kb raw admitted =
  andOfTrue
    (Admissible.hasEdgesProof admitted)
    ( andOfTrue
        (Admissible.predicateProof admitted)
        ( andOfTrue
            (Admissible.pathProof admitted)
            (Admissible.targetTypeProof admitted)
        )
    )

record AcceptedCertificate
  (kb : KnowledgeBase)
  (raw : RawCertificate)
  (strength : RawCertificate → Bool) : Set where

  constructor acceptedCertificate
  field
    acceptedAdmissible :
      Admissible kb raw

    acceptedStrength :
      strength raw ≡ true

open AcceptedCertificate public

acceptCertificate :
  (kb : KnowledgeBase) →
  (raw : RawCertificate) →
  (strength : RawCertificate → Bool) →
  check kb raw ≡ true →
  strength raw ≡ true →
  AcceptedCertificate kb raw strength
acceptCertificate kb raw strength checked strong =
  acceptedCertificate
    (checkSound kb raw checked)
    strong

record RuntimeClause : Set where
  constructor runtimeClause
  field
    clauseSubject   : String
    clausePredicate : String
    clauseObject    : String
    clauseForgetContext : ForgetContext

open RuntimeClause public

boolEqual : Bool → Bool → Bool
boolEqual true true = true
boolEqual false false = true
boolEqual _ _ = false

forgetContextEqual : ForgetContext → ForgetContext → Bool
forgetContextEqual left right =
  boolEqual (genericWholeFiber left) (genericWholeFiber right)
    and boolEqual (contextHasRestrictor left) (contextHasRestrictor right)
    and boolEqual (contextHasQuantifier left) (contextHasQuantifier right)
    and boolEqual (contextIsPositive left) (contextIsPositive right)
    and boolEqual (contextIsUnfocused left) (contextIsUnfocused right)
    and boolEqual (contextHasAnaphor left) (contextHasAnaphor right)
    and boolEqual (contextHasTemporal left) (contextHasTemporal right)

lexemeMatches :
  KnowledgeBase →
  String →
  String →
  Bool
lexemeMatches kb function entity =
  any matches (lexemeFacts kb)
  where
  matches : LexemeFact → Bool
  matches fact =
    stringEqual function (lexemeFunction fact)
      and stringEqual entity (lexemeEntity fact)

holeFunction : Hole → RuntimeClause → String
holeFunction subjectHole =
  clauseSubject
holeFunction objectHole =
  clauseObject

unchangedArgument : Hole → RuntimeClause → String
unchangedArgument subjectHole =
  clauseObject
unchangedArgument objectHole =
  clauseSubject

endpointMatches :
  KnowledgeBase →
  Direction →
  RuntimeClause →
  RuntimeClause →
  RawCertificate →
  Bool
endpointMatches kb expand before after raw =
  lexemeMatches kb
    (holeFunction (rawHole raw) before)
    (rawSource raw)
    and lexemeMatches kb
      (holeFunction (rawHole raw) after)
      (rawTarget raw)
endpointMatches kb contract before after raw =
  lexemeMatches kb
    (holeFunction (rawHole raw) before)
    (rawTarget raw)
    and lexemeMatches kb
      (holeFunction (rawHole raw) after)
      (rawSource raw)

directionSafe :
  KnowledgeBase →
  Direction →
  RawCertificate →
  Bool
directionSafe kb expand raw =
  true
directionSafe kb contract raw =
  hasType kb (rawTarget raw) "GenericReading"
    and forgetContextSafe (rawForgetContext raw)

rewriteMatches :
  KnowledgeBase →
  RuntimeClause →
  RuntimeClause →
  RawCertificate →
  Bool
rewriteMatches kb before after raw =
  stringEqual
    (clausePredicate before)
    (rawPredicate raw)
    and stringEqual
      (clausePredicate after)
      (rawPredicate raw)
    and stringEqual
      (unchangedArgument (rawHole raw) before)
      (unchangedArgument (rawHole raw) after)
    and forgetContextEqual
      (clauseForgetContext before)
      (rawForgetContext raw)
    and forgetContextEqual
      (clauseForgetContext after)
      (rawForgetContext raw)
    and endpointMatches
      kb
      (rawDirection raw)
      before
      after
      raw
    and directionSafe kb (rawDirection raw) raw

runtimeCheck :
  KnowledgeBase →
  RuntimeClause →
  RuntimeClause →
  RawCertificate →
  Bool
runtimeCheck kb before after raw =
  check kb raw
    and isHardRequirement raw
    and rewriteMatches kb before after raw

record RawLexicalAnchor : Set where
  constructor rawLexicalAnchor
  field
    rawAnchorConstructor : String
    rawAnchorLemma       : String
    rawAnchorSurface     : String
    rawAnchorStart       : Nat
    rawAnchorEnd         : Nat

data RawContextPayload : Set where
  rawRequires : Requirement → RawContextPayload
  rawRequiresRelation : String → String → RawContextPayload
  rawRequiresSome : String → Requirement → RawContextPayload
  rawPrefers : Requirement → RawContextPayload
  rawPrefersRelation : String → String → RawContextPayload
  rawPrefersSome : String → Requirement → RawContextPayload

record RawContextConstraint : Set where
  constructor rawContextConstraint
  field
    rawConstraintOrigin  : RawLexicalAnchor
    rawConstraintPayload : RawContextPayload
    rawConstraintProvenance : String

record RawContext : Set where
  constructor rawContext
  field
    rawContextSnapshotHash : String
    rawContextAction       : String
    rawContextConstraints  : List RawContextConstraint
    rawContextRules        : List String

open RawLexicalAnchor
open RawContextConstraint
open RawContext

lessThan : Nat → Nat → Bool
lessThan zero zero = false
lessThan zero (suc _) = true
lessThan (suc _) zero = false
lessThan (suc left) (suc right) = lessThan left right

anchorValid : RawLexicalAnchor → Bool
anchorValid anchor =
  not (stringEqual (rawAnchorConstructor anchor) "")
    and not (stringEqual (rawAnchorLemma anchor) "")
    and not (stringEqual (rawAnchorSurface anchor) "")
    and lessThan (rawAnchorStart anchor) (rawAnchorEnd anchor)

rawConstraintHolds :
  KnowledgeBase →
  String →
  RawContextConstraint →
  Bool
rawConstraintHolds kb candidate constraint with rawConstraintPayload constraint
... | rawRequires requirement =
  satisfiesRequirement kb candidate requirement
... | rawRequiresRelation relation target =
  relationExists kb (edge relation candidate target)
... | rawRequiresSome relation requirement =
  any matches (relationFacts kb)
  where
  matches : RelationFact → Bool
  matches fact =
    stringEqual relation (factRelation fact)
      and stringEqual candidate (factSource fact)
      and satisfiesRequirement kb (factTarget fact) requirement
... | rawPrefers _ = true
... | rawPrefersRelation _ _ = true
... | rawPrefersSome _ _ = true

rawPreferenceMatches :
  KnowledgeBase →
  String →
  RawContextConstraint →
  Bool
rawPreferenceMatches kb candidate constraint with rawConstraintPayload constraint
... | rawRequires _ = true
... | rawRequiresRelation _ _ = true
... | rawRequiresSome _ _ = true
... | rawPrefers requirement =
  satisfiesRequirement kb candidate requirement
... | rawPrefersRelation relation target =
  relationExists kb (edge relation candidate target)
... | rawPrefersSome relation requirement =
  any matches (relationFacts kb)
  where
  matches : RelationFact → Bool
  matches fact =
    stringEqual relation (factRelation fact)
      and stringEqual candidate (factSource fact)
      and satisfiesRequirement kb (factTarget fact) requirement

contextPreferenceCheck :
  KnowledgeBase →
  RawContextConstraint →
  String →
  Bool
contextPreferenceCheck kb constraint candidate =
  anchorValid (rawConstraintOrigin constraint)
    and not (stringEqual (rawConstraintProvenance constraint) "")
    and rawPreferenceMatches kb candidate constraint

preferenceRequirementDoesNotFilter :
  (kb : KnowledgeBase) →
  (candidate : String) →
  (anchor : RawLexicalAnchor) →
  (requirement : Requirement) →
  (provenance : String) →
  rawConstraintHolds
    kb
    candidate
    (rawContextConstraint anchor (rawPrefers requirement) provenance)
    ≡ true
preferenceRequirementDoesNotFilter kb candidate anchor requirement provenance =
  refl

preferenceRelationDoesNotFilter :
  (kb : KnowledgeBase) →
  (candidate relation target : String) →
  (anchor : RawLexicalAnchor) →
  (provenance : String) →
  rawConstraintHolds
    kb
    candidate
    (rawContextConstraint anchor (rawPrefersRelation relation target) provenance)
    ≡ true
preferenceRelationDoesNotFilter kb candidate relation target anchor provenance =
  refl

preferenceExistentialDoesNotFilter :
  (kb : KnowledgeBase) →
  (candidate relation : String) →
  (requirement : Requirement) →
  (anchor : RawLexicalAnchor) →
  (provenance : String) →
  rawConstraintHolds
    kb
    candidate
    (rawContextConstraint anchor (rawPrefersSome relation requirement) provenance)
    ≡ true
preferenceExistentialDoesNotFilter kb candidate relation requirement anchor provenance =
  refl

rawConstraintsHold :
  KnowledgeBase →
  String →
  List RawContextConstraint →
  Bool
rawConstraintsHold kb candidate [] = true
rawConstraintsHold kb candidate (constraint ∷ constraints) =
  anchorValid (rawConstraintOrigin constraint)
    and not (stringEqual (rawConstraintProvenance constraint) "")
    and rawConstraintHolds kb candidate constraint
    and rawConstraintsHold kb candidate constraints

allProvenanceKnown :
  List String →
  List RawContextConstraint →
  Bool
allProvenanceKnown rules [] = true
allProvenanceKnown rules (constraint ∷ constraints) =
  any
    (stringEqual (rawConstraintProvenance constraint))
    rules
    and allProvenanceKnown rules constraints

contextLayerCheck :
  KnowledgeBase →
  String →
  RawContext →
  String →
  Bool
contextLayerCheck kb snapshotHash context candidate =
  not (stringEqual snapshotHash "")
    and stringEqual snapshotHash (rawContextSnapshotHash context)
    and not (stringEqual (rawContextAction context) "")
    and rawConstraintsHold
      kb
      candidate
      (rawContextConstraints context)
    and allProvenanceKnown
      (rawContextRules context)
      (rawContextConstraints context)

record ContextLayerAccepted
  (kb : KnowledgeBase)
  (snapshotHash : String)
  (context : RawContext)
  (candidate : String) : Set where
  constructor contextLayerAccepted
  field
    layerCheckProof :
      contextLayerCheck kb snapshotHash context candidate ≡ true

contextLayerCheckSound :
  (kb : KnowledgeBase) →
  (snapshotHash : String) →
  (context : RawContext) →
  (candidate : String) →
  contextLayerCheck kb snapshotHash context candidate ≡ true →
  ContextLayerAccepted kb snapshotHash context candidate
contextLayerCheckSound kb snapshotHash context candidate checked =
  contextLayerAccepted checked

contextLayerCheckComplete :
  (kb : KnowledgeBase) →
  (snapshotHash : String) →
  (context : RawContext) →
  (candidate : String) →
  ContextLayerAccepted kb snapshotHash context candidate →
  contextLayerCheck kb snapshotHash context candidate ≡ true
contextLayerCheckComplete kb snapshotHash context candidate accepted =
  ContextLayerAccepted.layerCheckProof accepted

contextualRuntimeCheck :
  KnowledgeBase →
  RuntimeClause →
  RuntimeClause →
  RawCertificate →
  String →
  RawContext →
  Bool
contextualRuntimeCheck kb before after raw snapshotHash context =
  runtimeCheck kb before after raw
    and contextLayerCheck kb snapshotHash context (rawTarget raw)

record ContextualRuntimeAdmissible
  (kb : KnowledgeBase)
  (before after : RuntimeClause)
  (raw : RawCertificate)
  (snapshotHash : String)
  (context : RawContext) : Set where
  constructor contextualRuntimeAdmissible
  field
    contextualRuntimeProof :
      runtimeCheck kb before after raw ≡ true
    contextualLayer :
      ContextLayerAccepted
        kb snapshotHash context (rawTarget raw)

contextualRuntimeCheckSound :
  (kb : KnowledgeBase) →
  (before after : RuntimeClause) →
  (raw : RawCertificate) →
  (snapshotHash : String) →
  (context : RawContext) →
  contextualRuntimeCheck kb before after raw snapshotHash context ≡ true →
  ContextualRuntimeAdmissible kb before after raw snapshotHash context
contextualRuntimeCheckSound kb before after raw snapshotHash context checked =
  contextualRuntimeAdmissible
    runtimeChecked
    ( contextLayerCheckSound
      kb snapshotHash context (rawTarget raw) layerChecked
    )
  where
    runtimeChecked :
      runtimeCheck kb before after raw ≡ true
    runtimeChecked =
      andTrueLeft
        {left = runtimeCheck kb before after raw}
        {right = contextLayerCheck kb snapshotHash context (rawTarget raw)}
        checked

    layerChecked :
      contextLayerCheck kb snapshotHash context (rawTarget raw) ≡ true
    layerChecked =
      andTrueRight
        {left = runtimeCheck kb before after raw}
        {right = contextLayerCheck kb snapshotHash context (rawTarget raw)}
        checked

contextualRuntimeCheckComplete :
  (kb : KnowledgeBase) →
  (before after : RuntimeClause) →
  (raw : RawCertificate) →
  (snapshotHash : String) →
  (context : RawContext) →
  ContextualRuntimeAdmissible kb before after raw snapshotHash context →
  contextualRuntimeCheck kb before after raw snapshotHash context ≡ true
contextualRuntimeCheckComplete kb before after raw snapshotHash context admitted =
  andOfTrue
    (ContextualRuntimeAdmissible.contextualRuntimeProof admitted)
    ( contextLayerCheckComplete
      kb snapshotHash context (rawTarget raw)
      (ContextualRuntimeAdmissible.contextualLayer admitted)
    )

preferenceRuntimeCheck :
  KnowledgeBase →
  RuntimeClause →
  RuntimeClause →
  RawCertificate →
  Bool
preferenceRuntimeCheck kb before after raw =
  check kb raw
    and isSelectionalPreference raw
    and rewriteMatches kb before after raw

record RuntimeAdmissible
  (kb : KnowledgeBase)
  (before after : RuntimeClause)
  (raw : RawCertificate) : Set where

  constructor runtimeAdmissible
  field
    runtimeCertificate :
      AcceptedCertificate kb raw isHardRequirement

    runtimeRewrite :
      rewriteMatches kb before after raw ≡ true

open RuntimeAdmissible public

runtimeCheckSound :
  (kb : KnowledgeBase) →
  (before after : RuntimeClause) →
  (raw : RawCertificate) →
  runtimeCheck kb before after raw ≡ true →
  RuntimeAdmissible kb before after raw
runtimeCheckSound kb before after raw checked =
  runtimeAdmissible
    ( acceptCertificate
        kb
        raw
        isHardRequirement
        certificateChecked
        hardChecked
    )
    rewriteChecked
  where
  certificateChecked :
    check kb raw ≡ true
  certificateChecked =
    andTrueLeft
      {left = check kb raw}
      { right =
          isHardRequirement raw
            and rewriteMatches kb before after raw
      }
      checked

  restChecked :
    ( isHardRequirement raw
      and rewriteMatches kb before after raw
    ) ≡ true
  restChecked =
    andTrueRight
      {left = check kb raw}
      { right =
          isHardRequirement raw
            and rewriteMatches kb before after raw
      }
      checked

  hardChecked :
    isHardRequirement raw ≡ true
  hardChecked =
    andTrueLeft
      {left = isHardRequirement raw}
      {right = rewriteMatches kb before after raw}
      restChecked

  rewriteChecked :
    rewriteMatches kb before after raw ≡ true
  rewriteChecked =
    andTrueRight
      {left = isHardRequirement raw}
      {right = rewriteMatches kb before after raw}
      restChecked

record RawDiscourseEvidence : Set where
  constructor targetSalient
  field
    evidenceTarget : String
    evidenceSource : String

open RawDiscourseEvidence public

checkPromotion :
  RawCertificate →
  Maybe RawDiscourseEvidence →
  Bool
checkPromotion raw nothing =
  false
checkPromotion raw (just evidence) =
  isSelectionalPreference raw
    and stringEqual
      (rawTarget raw)
      (evidenceTarget evidence)
    and not
      (stringEqual (evidenceSource evidence) "")

record ValidatedDiscourseEvidence
  (raw : RawCertificate)
  (evidence : RawDiscourseEvidence) : Set where

  constructor validatedDiscourseEvidence
  field
    promotionAccepted :
      checkPromotion raw (just evidence) ≡ true

promotionSound :
  (raw : RawCertificate) →
  (evidence : RawDiscourseEvidence) →
  checkPromotion raw (just evidence) ≡ true →
  ValidatedDiscourseEvidence raw evidence
promotionSound raw evidence checked =
  validatedDiscourseEvidence checked

-- Coarse-reading compatibility: whether two accepted certificates may be
-- reported as the same coarse ("kind-level") reading rather than two
-- unrelated fine candidates -- the general, engine-exposed version of
-- what Metonymy.NovalisCoarseModel/EswatiniCoarseModel/RijekaCoarseModel
-- each hand-built for one specific real example.
--
-- Two certificates are compatible only when the requirement that
-- selected them both is a single, specific HasSort -- never AnyOf,
-- AllOf, or a negation. This is deliberate, not an oversight: a broad
-- disjunction like AnyOf [HasSort Animate, HasSort Organization] (e.g.
-- the "announce" requirement in the Waterloo fixture, before its second,
-- narrowing "in physics" signal is applied) can be satisfied by
-- genuinely heterogeneous entities -- a university, a research
-- institute, a city council -- that are not the same kind of thing and
-- must never be reported as one coarse reading. A single HasSort, by
-- contrast, only ever selects entities that are already the same
-- declared kind; the two real examples this narrows to (two literary
-- works, two cabinet formations, two football clubs) differ only in
-- which specific instance, never in what kind of thing they are.
isSingleHasSort : Requirement → Bool
isSingleHasSort (hasSort _) = true
isSingleHasSort (allOf _) = false
isSingleHasSort (anyOf _) = false
isSingleHasSort (notRequirement _) = false

-- Reached from the same entity by the same bridge relation: the first
-- (and, for every currently-verified real example, only) edge of each
-- certificate must agree on both endpoints.
sameFirstEdge : RawCertificate → RawCertificate → Bool
sameFirstEdge left right with rawEdges left | rawEdges right
... | (e1 ∷ _) | (e2 ∷ _) =
  stringEqual (edgeRelation e1) (edgeRelation e2)
    and stringEqual (edgeSource e1) (edgeSource e2)
... | _ | _ = false

compatibilityCheck : RawCertificate → RawCertificate → Bool
compatibilityCheck left right =
  isSingleHasSort (rawRequirement left)
    and requirementEqual (rawRequirement left) (rawRequirement right)
    and sameFirstEdge left right

record CompatibilityAccepted
  (left right : RawCertificate) : Set where
  constructor compatibilityAccepted
  field
    compatibilityAcceptedProof :
      compatibilityCheck left right ≡ true

compatibilityCheckSound :
  (left right : RawCertificate) →
  compatibilityCheck left right ≡ true →
  CompatibilityAccepted left right
compatibilityCheckSound left right checked =
  compatibilityAccepted checked

compatibilityCheckComplete :
  (left right : RawCertificate) →
  CompatibilityAccepted left right →
  compatibilityCheck left right ≡ true
compatibilityCheckComplete left right accepted =
  CompatibilityAccepted.compatibilityAcceptedProof accepted

