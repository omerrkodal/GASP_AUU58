// Copyright GASP_AUU58. All Rights Reserved.

#include "AsyncAction_LoadDataAsset.h"
#include "UObject/UnrealType.h"

// ─────────────────────────────────────────────────────────────────────────────

UAsyncAction_LoadDataAsset* UAsyncAction_LoadDataAsset::AsyncLoadDataAsset(
	UObject* WorldContextObject,
	UObject* DataAsset,
	bool bHighPriority)
{
	UAsyncAction_LoadDataAsset* Action = NewObject<UAsyncAction_LoadDataAsset>();
	Action->WorldContext      = WorldContextObject;
	Action->TargetDataAsset   = DataAsset;
	Action->bHighPriority     = bHighPriority;
	Action->RegisterWithGameInstance(WorldContextObject);
	return Action;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Deep reflection path collector
// ─────────────────────────────────────────────────────────────────────────────

void UAsyncAction_LoadDataAsset::CollectPathsFromStruct(
	const void* StructData,
	const UStruct* Struct,
	TArray<FSoftObjectPath>& OutPaths)
{
	if (!StructData || !Struct) return;

	for (TFieldIterator<FProperty> It(Struct); It; ++It)
	{
		const FProperty* Prop = *It;
		const void* ValuePtr = Prop->ContainerPtrToValuePtr<void>(StructData);

		// TSoftObjectPtr<T>
		if (const FSoftObjectProperty* SoftObj = CastField<FSoftObjectProperty>(Prop))
		{
			const FSoftObjectPtr& SoftPtr = *static_cast<const FSoftObjectPtr*>(ValuePtr);
			if (!SoftPtr.IsNull())
			{
				OutPaths.AddUnique(SoftPtr.ToSoftObjectPath());
			}
		}
		// TSoftClassPtr<T>
		else if (const FSoftClassProperty* SoftCls = CastField<FSoftClassProperty>(Prop))
		{
			const FSoftObjectPtr& SoftPtr = *static_cast<const FSoftObjectPtr*>(ValuePtr);
			if (!SoftPtr.IsNull())
			{
				OutPaths.AddUnique(SoftPtr.ToSoftObjectPath());
			}
		}
		// Nested struct — recurse into it
		else if (const FStructProperty* StructProp = CastField<FStructProperty>(Prop))
		{
			CollectPathsFromStruct(ValuePtr, StructProp->Struct, OutPaths);
		}
		// TArray — iterate elements
		else if (const FArrayProperty* ArrayProp = CastField<FArrayProperty>(Prop))
		{
			FScriptArrayHelper ArrayHelper(ArrayProp, ValuePtr);
			for (int32 i = 0; i < ArrayHelper.Num(); ++i)
			{
				const void* ElemPtr = ArrayHelper.GetRawPtr(i);

				if (const FSoftObjectProperty* InnerSoft = CastField<FSoftObjectProperty>(ArrayProp->Inner))
				{
					const FSoftObjectPtr& SoftPtr = *static_cast<const FSoftObjectPtr*>(ElemPtr);
					if (!SoftPtr.IsNull()) OutPaths.AddUnique(SoftPtr.ToSoftObjectPath());
				}
				else if (const FStructProperty* InnerStruct = CastField<FStructProperty>(ArrayProp->Inner))
				{
					CollectPathsFromStruct(ElemPtr, InnerStruct->Struct, OutPaths);
				}
			}
		}
		// TMap — iterate values (keys are usually enums/names, not soft refs)
		else if (const FMapProperty* MapProp = CastField<FMapProperty>(Prop))
		{
			FScriptMapHelper MapHelper(MapProp, ValuePtr);
			for (int32 i = 0; i < MapHelper.Num(); ++i)
			{
				if (!MapHelper.IsValidIndex(i)) continue;

				// Check the value property
				const void* ValPtr = MapHelper.GetValuePtr(i);

				if (const FSoftObjectProperty* InnerSoft = CastField<FSoftObjectProperty>(MapProp->ValueProp))
				{
					const FSoftObjectPtr& SoftPtr = *static_cast<const FSoftObjectPtr*>(ValPtr);
					if (!SoftPtr.IsNull()) OutPaths.AddUnique(SoftPtr.ToSoftObjectPath());
				}
				else if (const FStructProperty* InnerStruct = CastField<FStructProperty>(MapProp->ValueProp))
				{
					// This handles your case: TMap<EWeaponAction, FSAnimMontage>
					// where FSAnimMontage contains a TSoftObjectPtr<UAnimMontage>
					CollectPathsFromStruct(ValPtr, InnerStruct->Struct, OutPaths);
				}
			}
		}
	}
}

void UAsyncAction_LoadDataAsset::CollectPathsFromObject(
	UObject* Object,
	TArray<FSoftObjectPath>& OutPaths)
{
	if (!IsValid(Object)) return;
	CollectPathsFromStruct(Object, Object->GetClass(), OutPaths);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Async action lifecycle
// ─────────────────────────────────────────────────────────────────────────────

void UAsyncAction_LoadDataAsset::Activate()
{
	if (!IsValid(TargetDataAsset))
	{
		UE_LOG(LogTemp, Warning, TEXT("[AsyncLoadDataAsset] DataAsset is null."));
		OnFailed.Broadcast();
		SetReadyToDestroy();
		return;
	}

	TArray<FSoftObjectPath> Paths;
	CollectPathsFromObject(TargetDataAsset, Paths);

	if (Paths.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("[AsyncLoadDataAsset] No soft references found in '%s'."),
			*TargetDataAsset->GetName());
		OnFailed.Broadcast();
		SetReadyToDestroy();
		return;
	}

	UE_LOG(LogTemp, Log, TEXT("[AsyncLoadDataAsset] Loading %d soft ref(s) from '%s'..."),
		Paths.Num(), *TargetDataAsset->GetName());

	const TAsyncLoadPriority Priority = bHighPriority
		? FStreamableManager::AsyncLoadHighPriority
		: FStreamableManager::DefaultAsyncLoadPriority;

	Handle = UAssetManager::GetStreamableManager().RequestAsyncLoad(
		Paths,
		FStreamableDelegate::CreateUObject(this, &UAsyncAction_LoadDataAsset::OnLoadComplete),
		Priority,
		true
	);
}

void UAsyncAction_LoadDataAsset::OnLoadComplete()
{
	UE_LOG(LogTemp, Log, TEXT("[AsyncLoadDataAsset] All assets loaded for '%s'."),
		IsValid(TargetDataAsset) ? *TargetDataAsset->GetName() : TEXT("null"));

	OnLoaded.Broadcast();
	SetReadyToDestroy();
}
