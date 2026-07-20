// Copyright GASP_AUU58. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintAsyncActionBase.h"
#include "Engine/StreamableManager.h"
#include "Engine/AssetManager.h"
#include "AsyncAction_LoadSoftMap.generated.h"

// Simple no-param delegates - TMap cannot be passed through dynamic multicast delegates
// Blueprint retrieves results via GetResults() inside the OnLoaded event
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnSoftMapLoaded);

/**
 * Async node: takes a Map<FName, Soft Object Reference> and resolves it to
 * hard references. Fires OnLoaded when all assets are resident in memory.
 *
 * Blueprint usage:
 *   1. Build a Map<FName, Soft Object Reference> from your Data Asset
 *      (use Enum → Get Display Name as the key).
 *   2. Feed it into [Async Load Soft Map].
 *   3. In the OnLoaded event, call [Get Results] to get Map<FName, UObject*>.
 *   4. Use [Find] on the result map to get specific assets by name.
 */
UCLASS(meta=(HideThen=true))
class ASSETLOADER_API UAsyncAction_LoadSoftMap : public UBlueprintAsyncActionBase
{
	GENERATED_BODY()

public:

	/** Fires once when ALL values are loaded. Call GetResults() inside this event. */
	UPROPERTY(BlueprintAssignable)
	FOnSoftMapLoaded OnLoaded;

	/** Fires if the map was empty, all paths were null, or load failed. */
	UPROPERTY(BlueprintAssignable)
	FOnSoftMapLoaded OnFailed;

	/**
	 * Async-loads every Soft Object value in the map.
	 * Bind OnLoaded, then call GetResults() inside the event handler.
	 *
	 * @param SoftMap        Map<FName, Soft Object Reference>. Build this from your
	 *                       Data Asset using Enum → Get Display Name as the key.
	 * @param bHighPriority  True = load now (equipping weapon). False = background preload.
	 */
	UFUNCTION(BlueprintCallable, Category="AssetLoader",
	          meta=(BlueprintInternalUseOnly="true", WorldContext="WorldContextObject",
	                DisplayName="Async Load Soft Map",
	                ToolTip="Batch-loads all soft references in the map. Call Get Results inside OnLoaded."))
	static UAsyncAction_LoadSoftMap* AsyncLoadSoftMap(
		UObject* WorldContextObject,
		const TMap<FName, TSoftObjectPtr<UObject>>& SoftMap,
		bool bHighPriority = true);

	/**
	 * Returns the fully resolved Map<FName, UObject*>.
	 * Only valid to call inside the OnLoaded event.
	 */
	UFUNCTION(BlueprintPure, Category="AssetLoader",
	          meta=(DisplayName="Get Results",
	                ToolTip="Returns the resolved hard-reference map. Only valid inside OnLoaded."))
	const TMap<FName, UObject*>& GetResults() const { return ResolvedMap; }

	virtual void Activate() override;

private:
	void OnLoadComplete();

	UPROPERTY()
	TObjectPtr<UObject> WorldContext;

	TMap<FName, TSoftObjectPtr<UObject>> PendingMap;
	TMap<FName, UObject*> ResolvedMap;
	bool bHighPriority = true;

	TSharedPtr<FStreamableHandle> Handle;
};
