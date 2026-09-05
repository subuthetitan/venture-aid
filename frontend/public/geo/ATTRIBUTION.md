\# Geographic data attribution



\*\*District boundaries:\*\* DataMeet Community Maps

https://github.com/datameet/maps — `Districts/Census\_2011/2011\_Dist.shp`



\*\*Licence:\*\* CC BY 4.0



\*\*Processing:\*\* simplified with mapshaper at 4% with `keep-shapes`, output as

GeoJSON at 0.0001 precision. 641 districts retained, 820 KB. Boundaries are

approximate and not authoritative for administrative purposes.



\*\*Join key:\*\* `censuscode` (Census of India 2011 district code).



\## Known limitation: 2011 vintage



These are Census 2011 boundaries. Two present-day states do not exist in this

file and are represented by their pre-reorganisation parent states:



\- \*\*Telangana\*\* (formed 2014) — its ten districts appear under Andhra Pradesh:

&#x20; censuscodes 532–541 (Adilabad, Nizamabad, Karimnagar, Medak, Hyderabad,

&#x20; Rangareddy, Mahbubnagar, Nalgonda, Warangal, Khammam).

\- \*\*Ladakh\*\* (formed 2019) — appears under Jammu \& Kashmir:

&#x20; censuscodes 3 (Leh) and 4 (Kargil).



Our reachability layer reassigns these twelve codes to their current states.

Districts created after 2011 by subdivision are not represented separately.

