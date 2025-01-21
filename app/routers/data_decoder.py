from fastapi import APIRouter, HTTPException

from app.routers.models import DataDecodedPublic, DataDecoderInput
from app.services.data_decoder import DataDecoded, get_data_decoder_service

router = APIRouter(
    prefix="/data-decoder",
    tags=["data decoder"],
)


@router.post("", response_model=DataDecodedPublic)
async def data_decoder(
    input_data: DataDecoderInput,
) -> DataDecoded:
    data_decoder_service = await get_data_decoder_service()
    data_decoded = await data_decoder_service.get_data_decoded(
        input_data.data,
        address=input_data.to,
        chain_id=input_data.chain_id,
    )

    if data_decoded is None:
        raise HTTPException(
            status_code=404, detail="Cannot find function selector to decode data"
        )

    return data_decoded
