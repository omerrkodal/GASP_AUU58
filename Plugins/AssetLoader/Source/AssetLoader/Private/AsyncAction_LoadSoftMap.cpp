// Copyright GASP_AUU58. All Rights Reserved.

#include "AsyncAction_LoadSoftMap.h"
#include "Engine/AssetManager.h"

UAsyncAction_LoadSoftMap* UAsyncAction_LoadSoftMap::AsyncLoadSoftMap(
	UObject* WorldContextObject,
	const TMap<FName, TSoftObjectPtr<UObject>>& SoftMap,
	bool bHighPriority)
{
	UAsyncAction_LoadSoftMap* Action = NewObject<UAsyncAction_LoadSoftMap>();
	Action->WorldContext  = WorldContextObject;
	Action->PendingMap    = SoftMap;
	Action->bHighPriority = bHighPriority;
	Action->RegisterWithGameInstance(WorldContextObject);
	return Action;
}

void UAsyncAction_LoadSoftMap::Activate()
{
	// Collect valid paths from the soft ptr map
	TArray<FSoftObjectPath> Paths;
	for (const auto& Pair : PendingMap)
	{
		if (!Pair.Value.IsNull())
		{
			Paths.AddUnique(Pair.Value.ToSoftObjectPath());
		}
	}

	if (Paths.IsEmpty())
	{
		OnFailed.Broadcast();
		SetReadyToDestroy();
		return;
	}

	const TAsyncLoadPriority Priority = bHighPriority
		? FStreamableManager::AsyncLoadHighPriority
		: FStreamableManager::DefaultAsyncLoadPriority;

	Handle = UAssetManager::GetStreamableManager().RequestAsyncLoad(
		Paths,
		FStreamableDelegate::CreateUObject(this, &UAsyncAction_LoadSoftMap::OnLoadComplete),
		Priority,
		true
	);
}

void UAsyncAction_LoadSoftMap::OnLoadComplete()
{
	// Resolve every soft ptr into a hard ptr and store in ResolvedMap
	ResolvedMap.Empty(PendingMap.Num());
	for (const auto& Pair : PendingMap)
	{
		UObject* Resolved = Pair.Value.IsValid() ? Pair.Value.Get() : nullptr;
		ResolvedMap.Add(Pair.Key, Resolved);
	}

	OnLoaded.Broadcast();
	SetReadyToDestroy();
}
