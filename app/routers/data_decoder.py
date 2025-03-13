from typing import cast

from fastapi import APIRouter, HTTPException

from eth_typing import Address

from app.routers.models import (
    DataDecodedPublic,
    DataDecoderInput,
    ParameterDecodedPublic,
)
from app.services.data_decoder import get_data_decoder_service

router = APIRouter(
    prefix="/data-decoder",
    tags=["data decoder"],
)


@router.post(
    "",
    response_model=DataDecodedPublic,
    summary="Decode provided data",
    response_description="Decoded data if it can be decoded",
)
async def data_decoder(input_data: DataDecoderInput) -> DataDecodedPublic:
    """
    Decode provided data if there's a matching ABI on the database. Accuracy of the decoding
    can be:

    - *FULL_MATCH*: Matched contract address and chain id.
    - *PARTIAL_MATCH* Matched contract address, but not chain id.
    - *ONLY_FUNCTION_MATCH*: Matched function from another contract.
    - *NO_MATCH*: Selector cannot be decoded.
    """
    data_decoder_service = await get_data_decoder_service()

    # Load new ABIs from the database, don't await it so they are loaded while calling `get_data_decoded`
    task_load_new_abis = data_decoder_service.load_new_abis()

    data_decoded = await data_decoder_service.get_data_decoded(
        input_data.data,
        address=cast(Address, input_data.to),
        chain_id=input_data.chain_id,
    )

    await task_load_new_abis
    if data_decoded is None:
        raise HTTPException(
            status_code=404, detail="Cannot find function selector to decode data"
        )

    decoding_accuracy = await data_decoder_service.get_decoding_accuracy(
        input_data.data,
        address=cast(Address, input_data.to),
        chain_id=input_data.chain_id,
    )
    return DataDecodedPublic(
        method=data_decoded["method"],
        parameters=cast(list[ParameterDecodedPublic], data_decoded["parameters"]),
        accuracy=decoding_accuracy,
    )
