from data_holders import SingleAssetData


class SingleAssetDataRepresentation(SingleAssetData):
    """
    If you need to add logic for dynamically generating traits(properties, levels, stats)
    or any other customization -> inherit from SingleAssetData, and override methods

    Last inheritor will be used as asset data holder
    """
    ...
