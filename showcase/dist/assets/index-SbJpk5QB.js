import{M as re,O as pe,B as ge,F as te,S as C,U as N,V as f,W as F,H as $,N as ve,C as be,a as U,b as S,A as oe,c as we,R as ye,d as xe,e as Ce,L as Se,f as Te,g as Me,h as Ee,i as Ae,j as Re,P as _e,k as Pe,l as Le,I as Be,m as O,n as Ie,o as De,p as Fe,q as $e}from"./three-D8n-YDYp.js";import{g as L}from"./gsap-SFc2wnMY.js";(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))s(r);new MutationObserver(r=>{for(const i of r)if(i.type==="childList")for(const a of i.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&s(a)}).observe(document,{childList:!0,subtree:!0});function t(r){const i={};return r.integrity&&(i.integrity=r.integrity),r.referrerPolicy&&(i.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?i.credentials="include":r.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function s(r){if(r.ep)return;r.ep=!0;const i=t(r);fetch(r.href,i)}})();const ne={name:"CopyShader",uniforms:{tDiffuse:{value:null},opacity:{value:1}},vertexShader:`

		varying vec2 vUv;

		void main() {

			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		uniform float opacity;

		uniform sampler2D tDiffuse;

		varying vec2 vUv;

		void main() {

			vec4 texel = texture2D( tDiffuse, vUv );
			gl_FragColor = opacity * texel;


		}`};class M{constructor(){this.isPass=!0,this.enabled=!0,this.needsSwap=!0,this.clear=!1,this.renderToScreen=!1}setSize(){}render(){console.error("THREE.Pass: .render() must be implemented in derived pass.")}dispose(){}}const Ne=new pe(-1,1,1,-1,0,1);class Ue extends ge{constructor(){super(),this.setAttribute("position",new te([-1,3,0,-1,-1,0,3,-1,0],3)),this.setAttribute("uv",new te([0,2,0,0,2,0],2))}}const ze=new Ue;class Q{constructor(e){this._mesh=new re(ze,e)}dispose(){this._mesh.geometry.dispose()}render(e){e.render(this._mesh,Ne)}get material(){return this._mesh.material}set material(e){this._mesh.material=e}}class He extends M{constructor(e,t){super(),this.textureID=t!==void 0?t:"tDiffuse",e instanceof C?(this.uniforms=e.uniforms,this.material=e):e&&(this.uniforms=N.clone(e.uniforms),this.material=new C({name:e.name!==void 0?e.name:"unspecified",defines:Object.assign({},e.defines),uniforms:this.uniforms,vertexShader:e.vertexShader,fragmentShader:e.fragmentShader})),this.fsQuad=new Q(this.material)}render(e,t,s){this.uniforms[this.textureID]&&(this.uniforms[this.textureID].value=s.texture),this.fsQuad.material=this.material,this.renderToScreen?(e.setRenderTarget(null),this.fsQuad.render(e)):(e.setRenderTarget(t),this.clear&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),this.fsQuad.render(e))}dispose(){this.material.dispose(),this.fsQuad.dispose()}}class ie extends M{constructor(e,t){super(),this.scene=e,this.camera=t,this.clear=!0,this.needsSwap=!1,this.inverse=!1}render(e,t,s){const r=e.getContext(),i=e.state;i.buffers.color.setMask(!1),i.buffers.depth.setMask(!1),i.buffers.color.setLocked(!0),i.buffers.depth.setLocked(!0);let a,n;this.inverse?(a=0,n=1):(a=1,n=0),i.buffers.stencil.setTest(!0),i.buffers.stencil.setOp(r.REPLACE,r.REPLACE,r.REPLACE),i.buffers.stencil.setFunc(r.ALWAYS,a,4294967295),i.buffers.stencil.setClear(n),i.buffers.stencil.setLocked(!0),e.setRenderTarget(s),this.clear&&e.clear(),e.render(this.scene,this.camera),e.setRenderTarget(t),this.clear&&e.clear(),e.render(this.scene,this.camera),i.buffers.color.setLocked(!1),i.buffers.depth.setLocked(!1),i.buffers.color.setMask(!0),i.buffers.depth.setMask(!0),i.buffers.stencil.setLocked(!1),i.buffers.stencil.setFunc(r.EQUAL,1,4294967295),i.buffers.stencil.setOp(r.KEEP,r.KEEP,r.KEEP),i.buffers.stencil.setLocked(!0)}}class Oe extends M{constructor(){super(),this.needsSwap=!1}render(e){e.state.buffers.stencil.setLocked(!1),e.state.buffers.stencil.setTest(!1)}}class ke{constructor(e,t){if(this.renderer=e,this._pixelRatio=e.getPixelRatio(),t===void 0){const s=e.getSize(new f);this._width=s.width,this._height=s.height,t=new F(this._width*this._pixelRatio,this._height*this._pixelRatio,{type:$}),t.texture.name="EffectComposer.rt1"}else this._width=t.width,this._height=t.height;this.renderTarget1=t,this.renderTarget2=t.clone(),this.renderTarget2.texture.name="EffectComposer.rt2",this.writeBuffer=this.renderTarget1,this.readBuffer=this.renderTarget2,this.renderToScreen=!0,this.passes=[],this.copyPass=new He(ne),this.copyPass.material.blending=ve,this.clock=new be}swapBuffers(){const e=this.readBuffer;this.readBuffer=this.writeBuffer,this.writeBuffer=e}addPass(e){this.passes.push(e),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}insertPass(e,t){this.passes.splice(t,0,e),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}removePass(e){const t=this.passes.indexOf(e);t!==-1&&this.passes.splice(t,1)}isLastEnabledPass(e){for(let t=e+1;t<this.passes.length;t++)if(this.passes[t].enabled)return!1;return!0}render(e){e===void 0&&(e=this.clock.getDelta());const t=this.renderer.getRenderTarget();let s=!1;for(let r=0,i=this.passes.length;r<i;r++){const a=this.passes[r];if(a.enabled!==!1){if(a.renderToScreen=this.renderToScreen&&this.isLastEnabledPass(r),a.render(this.renderer,this.writeBuffer,this.readBuffer,e,s),a.needsSwap){if(s){const n=this.renderer.getContext(),l=this.renderer.state.buffers.stencil;l.setFunc(n.NOTEQUAL,1,4294967295),this.copyPass.render(this.renderer,this.writeBuffer,this.readBuffer,e),l.setFunc(n.EQUAL,1,4294967295)}this.swapBuffers()}ie!==void 0&&(a instanceof ie?s=!0:a instanceof Oe&&(s=!1))}}this.renderer.setRenderTarget(t)}reset(e){if(e===void 0){const t=this.renderer.getSize(new f);this._pixelRatio=this.renderer.getPixelRatio(),this._width=t.width,this._height=t.height,e=this.renderTarget1.clone(),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}this.renderTarget1.dispose(),this.renderTarget2.dispose(),this.renderTarget1=e,this.renderTarget2=e.clone(),this.writeBuffer=this.renderTarget1,this.readBuffer=this.renderTarget2}setSize(e,t){this._width=e,this._height=t;const s=this._width*this._pixelRatio,r=this._height*this._pixelRatio;this.renderTarget1.setSize(s,r),this.renderTarget2.setSize(s,r);for(let i=0;i<this.passes.length;i++)this.passes[i].setSize(s,r)}setPixelRatio(e){this._pixelRatio=e,this.setSize(this._width,this._height)}dispose(){this.renderTarget1.dispose(),this.renderTarget2.dispose(),this.copyPass.dispose()}}class Ge extends M{constructor(e,t,s=null,r=null,i=null){super(),this.scene=e,this.camera=t,this.overrideMaterial=s,this.clearColor=r,this.clearAlpha=i,this.clear=!0,this.clearDepth=!1,this.needsSwap=!1,this._oldClearColor=new U}render(e,t,s){const r=e.autoClear;e.autoClear=!1;let i,a;this.overrideMaterial!==null&&(a=this.scene.overrideMaterial,this.scene.overrideMaterial=this.overrideMaterial),this.clearColor!==null&&(e.getClearColor(this._oldClearColor),e.setClearColor(this.clearColor)),this.clearAlpha!==null&&(i=e.getClearAlpha(),e.setClearAlpha(this.clearAlpha)),this.clearDepth==!0&&e.clearDepth(),e.setRenderTarget(this.renderToScreen?null:s),this.clear===!0&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),e.render(this.scene,this.camera),this.clearColor!==null&&e.setClearColor(this._oldClearColor),this.clearAlpha!==null&&e.setClearAlpha(i),this.overrideMaterial!==null&&(this.scene.overrideMaterial=a),e.autoClear=r}}const qe={uniforms:{tDiffuse:{value:null},luminosityThreshold:{value:1},smoothWidth:{value:1},defaultColor:{value:new U(0)},defaultOpacity:{value:0}},vertexShader:`

		varying vec2 vUv;

		void main() {

			vUv = uv;

			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		uniform sampler2D tDiffuse;
		uniform vec3 defaultColor;
		uniform float defaultOpacity;
		uniform float luminosityThreshold;
		uniform float smoothWidth;

		varying vec2 vUv;

		void main() {

			vec4 texel = texture2D( tDiffuse, vUv );

			vec3 luma = vec3( 0.299, 0.587, 0.114 );

			float v = dot( texel.xyz, luma );

			vec4 outputColor = vec4( defaultColor.rgb, defaultOpacity );

			float alpha = smoothstep( luminosityThreshold, luminosityThreshold + smoothWidth, v );

			gl_FragColor = mix( outputColor, texel, alpha );

		}`};class T extends M{constructor(e,t,s,r){super(),this.strength=t!==void 0?t:1,this.radius=s,this.threshold=r,this.resolution=e!==void 0?new f(e.x,e.y):new f(256,256),this.clearColor=new U(0,0,0),this.renderTargetsHorizontal=[],this.renderTargetsVertical=[],this.nMips=5;let i=Math.round(this.resolution.x/2),a=Math.round(this.resolution.y/2);this.renderTargetBright=new F(i,a,{type:$}),this.renderTargetBright.texture.name="UnrealBloomPass.bright",this.renderTargetBright.texture.generateMipmaps=!1;for(let u=0;u<this.nMips;u++){const y=new F(i,a,{type:$});y.texture.name="UnrealBloomPass.h"+u,y.texture.generateMipmaps=!1,this.renderTargetsHorizontal.push(y);const g=new F(i,a,{type:$});g.texture.name="UnrealBloomPass.v"+u,g.texture.generateMipmaps=!1,this.renderTargetsVertical.push(g),i=Math.round(i/2),a=Math.round(a/2)}const n=qe;this.highPassUniforms=N.clone(n.uniforms),this.highPassUniforms.luminosityThreshold.value=r,this.highPassUniforms.smoothWidth.value=.01,this.materialHighPassFilter=new C({uniforms:this.highPassUniforms,vertexShader:n.vertexShader,fragmentShader:n.fragmentShader}),this.separableBlurMaterials=[];const l=[3,5,7,9,11];i=Math.round(this.resolution.x/2),a=Math.round(this.resolution.y/2);for(let u=0;u<this.nMips;u++)this.separableBlurMaterials.push(this.getSeperableBlurMaterial(l[u])),this.separableBlurMaterials[u].uniforms.invSize.value=new f(1/i,1/a),i=Math.round(i/2),a=Math.round(a/2);this.compositeMaterial=this.getCompositeMaterial(this.nMips),this.compositeMaterial.uniforms.blurTexture1.value=this.renderTargetsVertical[0].texture,this.compositeMaterial.uniforms.blurTexture2.value=this.renderTargetsVertical[1].texture,this.compositeMaterial.uniforms.blurTexture3.value=this.renderTargetsVertical[2].texture,this.compositeMaterial.uniforms.blurTexture4.value=this.renderTargetsVertical[3].texture,this.compositeMaterial.uniforms.blurTexture5.value=this.renderTargetsVertical[4].texture,this.compositeMaterial.uniforms.bloomStrength.value=t,this.compositeMaterial.uniforms.bloomRadius.value=.1;const c=[1,.8,.6,.4,.2];this.compositeMaterial.uniforms.bloomFactors.value=c,this.bloomTintColors=[new S(1,1,1),new S(1,1,1),new S(1,1,1),new S(1,1,1),new S(1,1,1)],this.compositeMaterial.uniforms.bloomTintColors.value=this.bloomTintColors;const w=ne;this.copyUniforms=N.clone(w.uniforms),this.blendMaterial=new C({uniforms:this.copyUniforms,vertexShader:w.vertexShader,fragmentShader:w.fragmentShader,blending:oe,depthTest:!1,depthWrite:!1,transparent:!0}),this.enabled=!0,this.needsSwap=!1,this._oldClearColor=new U,this.oldClearAlpha=1,this.basic=new we,this.fsQuad=new Q(null)}dispose(){for(let e=0;e<this.renderTargetsHorizontal.length;e++)this.renderTargetsHorizontal[e].dispose();for(let e=0;e<this.renderTargetsVertical.length;e++)this.renderTargetsVertical[e].dispose();this.renderTargetBright.dispose();for(let e=0;e<this.separableBlurMaterials.length;e++)this.separableBlurMaterials[e].dispose();this.compositeMaterial.dispose(),this.blendMaterial.dispose(),this.basic.dispose(),this.fsQuad.dispose()}setSize(e,t){let s=Math.round(e/2),r=Math.round(t/2);this.renderTargetBright.setSize(s,r);for(let i=0;i<this.nMips;i++)this.renderTargetsHorizontal[i].setSize(s,r),this.renderTargetsVertical[i].setSize(s,r),this.separableBlurMaterials[i].uniforms.invSize.value=new f(1/s,1/r),s=Math.round(s/2),r=Math.round(r/2)}render(e,t,s,r,i){e.getClearColor(this._oldClearColor),this.oldClearAlpha=e.getClearAlpha();const a=e.autoClear;e.autoClear=!1,e.setClearColor(this.clearColor,0),i&&e.state.buffers.stencil.setTest(!1),this.renderToScreen&&(this.fsQuad.material=this.basic,this.basic.map=s.texture,e.setRenderTarget(null),e.clear(),this.fsQuad.render(e)),this.highPassUniforms.tDiffuse.value=s.texture,this.highPassUniforms.luminosityThreshold.value=this.threshold,this.fsQuad.material=this.materialHighPassFilter,e.setRenderTarget(this.renderTargetBright),e.clear(),this.fsQuad.render(e);let n=this.renderTargetBright;for(let l=0;l<this.nMips;l++)this.fsQuad.material=this.separableBlurMaterials[l],this.separableBlurMaterials[l].uniforms.colorTexture.value=n.texture,this.separableBlurMaterials[l].uniforms.direction.value=T.BlurDirectionX,e.setRenderTarget(this.renderTargetsHorizontal[l]),e.clear(),this.fsQuad.render(e),this.separableBlurMaterials[l].uniforms.colorTexture.value=this.renderTargetsHorizontal[l].texture,this.separableBlurMaterials[l].uniforms.direction.value=T.BlurDirectionY,e.setRenderTarget(this.renderTargetsVertical[l]),e.clear(),this.fsQuad.render(e),n=this.renderTargetsVertical[l];this.fsQuad.material=this.compositeMaterial,this.compositeMaterial.uniforms.bloomStrength.value=this.strength,this.compositeMaterial.uniforms.bloomRadius.value=this.radius,this.compositeMaterial.uniforms.bloomTintColors.value=this.bloomTintColors,e.setRenderTarget(this.renderTargetsHorizontal[0]),e.clear(),this.fsQuad.render(e),this.fsQuad.material=this.blendMaterial,this.copyUniforms.tDiffuse.value=this.renderTargetsHorizontal[0].texture,i&&e.state.buffers.stencil.setTest(!0),this.renderToScreen?(e.setRenderTarget(null),this.fsQuad.render(e)):(e.setRenderTarget(s),this.fsQuad.render(e)),e.setClearColor(this._oldClearColor,this.oldClearAlpha),e.autoClear=a}getSeperableBlurMaterial(e){const t=[];for(let s=0;s<e;s++)t.push(.39894*Math.exp(-.5*s*s/(e*e))/e);return new C({defines:{KERNEL_RADIUS:e},uniforms:{colorTexture:{value:null},invSize:{value:new f(.5,.5)},direction:{value:new f(.5,.5)},gaussianCoefficients:{value:t}},vertexShader:`varying vec2 vUv;
				void main() {
					vUv = uv;
					gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
				}`,fragmentShader:`#include <common>
				varying vec2 vUv;
				uniform sampler2D colorTexture;
				uniform vec2 invSize;
				uniform vec2 direction;
				uniform float gaussianCoefficients[KERNEL_RADIUS];

				void main() {
					float weightSum = gaussianCoefficients[0];
					vec3 diffuseSum = texture2D( colorTexture, vUv ).rgb * weightSum;
					for( int i = 1; i < KERNEL_RADIUS; i ++ ) {
						float x = float(i);
						float w = gaussianCoefficients[i];
						vec2 uvOffset = direction * invSize * x;
						vec3 sample1 = texture2D( colorTexture, vUv + uvOffset ).rgb;
						vec3 sample2 = texture2D( colorTexture, vUv - uvOffset ).rgb;
						diffuseSum += (sample1 + sample2) * w;
						weightSum += 2.0 * w;
					}
					gl_FragColor = vec4(diffuseSum/weightSum, 1.0);
				}`})}getCompositeMaterial(e){return new C({defines:{NUM_MIPS:e},uniforms:{blurTexture1:{value:null},blurTexture2:{value:null},blurTexture3:{value:null},blurTexture4:{value:null},blurTexture5:{value:null},bloomStrength:{value:1},bloomFactors:{value:null},bloomTintColors:{value:null},bloomRadius:{value:0}},vertexShader:`varying vec2 vUv;
				void main() {
					vUv = uv;
					gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
				}`,fragmentShader:`varying vec2 vUv;
				uniform sampler2D blurTexture1;
				uniform sampler2D blurTexture2;
				uniform sampler2D blurTexture3;
				uniform sampler2D blurTexture4;
				uniform sampler2D blurTexture5;
				uniform float bloomStrength;
				uniform float bloomRadius;
				uniform float bloomFactors[NUM_MIPS];
				uniform vec3 bloomTintColors[NUM_MIPS];

				float lerpBloomFactor(const in float factor) {
					float mirrorFactor = 1.2 - factor;
					return mix(factor, mirrorFactor, bloomRadius);
				}

				void main() {
					gl_FragColor = bloomStrength * ( lerpBloomFactor(bloomFactors[0]) * vec4(bloomTintColors[0], 1.0) * texture2D(blurTexture1, vUv) +
						lerpBloomFactor(bloomFactors[1]) * vec4(bloomTintColors[1], 1.0) * texture2D(blurTexture2, vUv) +
						lerpBloomFactor(bloomFactors[2]) * vec4(bloomTintColors[2], 1.0) * texture2D(blurTexture3, vUv) +
						lerpBloomFactor(bloomFactors[3]) * vec4(bloomTintColors[3], 1.0) * texture2D(blurTexture4, vUv) +
						lerpBloomFactor(bloomFactors[4]) * vec4(bloomTintColors[4], 1.0) * texture2D(blurTexture5, vUv) );
				}`})}}T.BlurDirectionX=new f(1,0);T.BlurDirectionY=new f(0,1);const We={name:"OutputShader",uniforms:{tDiffuse:{value:null},toneMappingExposure:{value:1}},vertexShader:`
		precision highp float;

		uniform mat4 modelViewMatrix;
		uniform mat4 projectionMatrix;

		attribute vec3 position;
		attribute vec2 uv;

		varying vec2 vUv;

		void main() {

			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`
	
		precision highp float;

		uniform sampler2D tDiffuse;

		#include <tonemapping_pars_fragment>
		#include <colorspace_pars_fragment>

		varying vec2 vUv;

		void main() {

			gl_FragColor = texture2D( tDiffuse, vUv );

			// tone mapping

			#ifdef LINEAR_TONE_MAPPING

				gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );

			#elif defined( REINHARD_TONE_MAPPING )

				gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );

			#elif defined( CINEON_TONE_MAPPING )

				gl_FragColor.rgb = OptimizedCineonToneMapping( gl_FragColor.rgb );

			#elif defined( ACES_FILMIC_TONE_MAPPING )

				gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );

			#elif defined( AGX_TONE_MAPPING )

				gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );

			#endif

			// color space

			#ifdef SRGB_TRANSFER

				gl_FragColor = sRGBTransferOETF( gl_FragColor );

			#endif

		}`};class Qe extends M{constructor(){super();const e=We;this.uniforms=N.clone(e.uniforms),this.material=new ye({name:e.name,uniforms:this.uniforms,vertexShader:e.vertexShader,fragmentShader:e.fragmentShader}),this.fsQuad=new Q(this.material),this._outputColorSpace=null,this._toneMapping=null}render(e,t,s){this.uniforms.tDiffuse.value=s.texture,this.uniforms.toneMappingExposure.value=e.toneMappingExposure,(this._outputColorSpace!==e.outputColorSpace||this._toneMapping!==e.toneMapping)&&(this._outputColorSpace=e.outputColorSpace,this._toneMapping=e.toneMapping,this.material.defines={},xe.getTransfer(this._outputColorSpace)===Ce&&(this.material.defines.SRGB_TRANSFER=""),this._toneMapping===Se?this.material.defines.LINEAR_TONE_MAPPING="":this._toneMapping===Te?this.material.defines.REINHARD_TONE_MAPPING="":this._toneMapping===Me?this.material.defines.CINEON_TONE_MAPPING="":this._toneMapping===Ee?this.material.defines.ACES_FILMIC_TONE_MAPPING="":this._toneMapping===Ae&&(this.material.defines.AGX_TONE_MAPPING=""),this.material.needsUpdate=!0),this.renderToScreen===!0?(e.setRenderTarget(null),this.fsQuad.render(e)):(e.setRenderTarget(t),this.clear&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),this.fsQuad.render(e))}dispose(){this.material.dispose(),this.fsQuad.dispose()}}const q=["0","1","2","3","4","5","6","7","8","9","$",".","-","+",",","?","✓","·","→"],le=["3,912.44","113.44","DR","CR","1310","6810","6410","1250","GL","AP","AR","JE","FX","EUR","P-0317","403","SHA-256"],V=[...q,...le],_=8,ce=Math.ceil(V.length/_),E=512,B=128,Ve=.62;function je(o){return function(){o|=0,o=o+1831565813|0;const e=Math.imul(o^o>>>15,1|o),t=e+Math.imul(e^e>>>7,61|e)^e;return((t^t>>>14)>>>0)/4294967296}}const A=je(20261025);function Je(){const o=document.createElement("canvas");o.width=E*_,o.height=B*ce;const e=o.getContext("2d");e.fillStyle="#000",e.fillRect(0,0,o.width,o.height),e.fillStyle="#fff",e.textAlign="center",e.textBaseline="middle",V.forEach((s,r)=>{const i=r%_,a=Math.floor(r/_);let n=B*Ve;e.font=`600 ${n}px Fira Mono, monospace`;const l=e.measureText(s).width;l>E*.94&&(n*=E*.94/l,e.font=`600 ${n}px Fira Mono, monospace`),e.fillText(s,i*E+E/2,a*B+B/2)});const t=new De(o);return t.generateMipmaps=!0,t.minFilter=Fe,t.magFilter=$e,t}function Ke(){const o=document.getElementById("particle-canvas");if(!o)return;const e=window.innerWidth<768,t=window.matchMedia("(prefers-reduced-motion: reduce)").matches,s=new Re,r=new _e(38,window.innerWidth/window.innerHeight,.1,100);r.position.set(0,3.1,11.2),r.lookAt(0,.9,-2.2);const i=new Pe({canvas:o,alpha:!0,antialias:!e,powerPreference:e?"low-power":"high-performance"});i.setPixelRatio(Math.min(window.devicePixelRatio,e?1:2)),i.setSize(window.innerWidth,window.innerHeight),i.setClearColor(0,0);const a=new ke(i);a.setPixelRatio(i.getPixelRatio()),a.setSize(window.innerWidth,window.innerHeight),a.addPass(new Ge(s,r));const n=new T(new f(window.innerWidth,window.innerHeight),e?.5:.95,.5,.22);a.addPass(n),a.addPass(new Qe);const l=e?48:64,c=e?64:96,w=.42,u=.22,y=5.2,g=l*c,he=Je(),P=new Float32Array(g*3),j=new Float32Array(g*4),J=new Float32Array(g*2);for(let d=0;d<c;d++)for(let v=0;v<l;v++){const h=d*l+v;P[h*3]=(v-(l-1)/2)*w,P[h*3+1]=0,P[h*3+2]=y-d*u,j.set([A(),A(),A(),A()],h*4);const me=Math.floor(A()*V.length);J.set([me,0],h*2)}const z=new Le(1,1),p=new Be;p.index=z.index,p.setAttribute("position",z.attributes.position),p.setAttribute("uv",z.attributes.uv),p.setAttribute("aGrid",new O(P,3)),p.setAttribute("aSeed",new O(j,4)),p.setAttribute("aInfo",new O(J,2)),p.instanceCount=g,p.boundingSphere=new Ie(new S,60);const K=new C({transparent:!0,depthWrite:!1,blending:oe,uniforms:{uTime:{value:0},uBlob:{value:0},uScroll:{value:0},uAtlas:{value:he},uCols:{value:_},uRows:{value:ce}},vertexShader:`
      uniform float uTime, uBlob, uScroll;
      uniform float uCols, uRows;
      attribute vec3 aGrid;
      attribute vec4 aSeed;
      attribute vec2 aInfo;
      varying vec2 vUv;
      varying vec3 vColor;
      varying float vAlpha;
      
      float hash(float n) { return fract(sin(n) * 43758.5453123); }
      
      vec3 hsv2rgb(vec3 c) {
        vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
        vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
        return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
      }
      
      void main() {
        float t = uTime;
        vec3 g = aGrid;
        vec2 blobC = vec2(0.0, -2.6);
        vec2 d2 = g.xz - blobC;
        float d = length(d2);
        
        float h = sin(g.x * 0.16 + t * 0.34) * cos(g.z * 0.17 + t * 0.34) * 2.3;
        float R = 3.9;
        float b = exp(-d * d / (R * R));
        float dome = uBlob * b * (2.7 + sin(t + d) * 0.5);
        
        vec3 p = g + vec3(0.0, h + dome, 0.0) * (1.0 - uScroll * 0.8);
        
        vec3 camR = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 camU = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        
        float s = 0.16 * (0.7 + 0.65 * aSeed.w) * (1.0 + 0.12 * b * uBlob);
        vec3 world = p + position.x * 4.0 * s * camR + position.y * s * camU;
        
        float rate = 2.5 + aSeed.y * 8.0;
        float tick = floor(t * rate + aSeed.z * 17.0);
        float r1 = hash(aSeed.x * 91.7 + tick * 1.37);
        float glyphIdx = r1 < 0.7 ? floor(r1 / 0.7 * ${q.length}.0) : ${q.length}.0 + floor((r1 - 0.7) / 0.3 * ${le.length}.0);
        
        float colI = mod(glyphIdx, uCols);
        float rowI = floor(glyphIdx / uCols);
        vUv = vec2((colI + uv.x) / uCols, 1.0 - (rowI + 1.0 - uv.y) / uRows);
        
        float hn = clamp((h + dome * 0.7 + 0.5) / 2.4, 0.0, 1.0);
        float hue = mix(0.03, 0.09, hn);
        float sat = mix(0.8, 0.9, hn);
        float val = mix(0.4, 1.0, hn * hn);
        vColor = hsv2rgb(vec3(hue, sat, val));
        
        vec4 mv = viewMatrix * vec4(world, 1.0);
        float depth = -mv.z;
        float fog = (1.0 - smoothstep(13.0, 30.0, depth)) * smoothstep(0.8, 2.5, depth);
        vAlpha = fog * (1.0 - uScroll * 0.5);
        
        gl_Position = projectionMatrix * mv;
      }
    `,fragmentShader:`
      precision highp float;
      uniform sampler2D uAtlas;
      varying vec2 vUv;
      varying vec3 vColor;
      varying float vAlpha;
      
      void main() {
        float a = texture2D(uAtlas, vUv).r;
        a = smoothstep(0.02, 0.9, a);
        if (a * vAlpha < 0.002) discard;
        gl_FragColor = vec4(vColor * a * vAlpha, 1.0);
      }
    `}),X=new re(p,K);X.frustumCulled=!1,s.add(X);const Y=document.getElementById("hero-labels");Y&&!t&&[{text:"PAYPAL *INST XFER −$3,912.44",x:50,y:12},{text:"1310 · $3,451.50 · EUR crew deposit",x:75,y:28},{text:"6810 · $147.50 · wire fees",x:25,y:72,brightness:1.3},{text:"6410 · $200.00 · Claude API",x:80,y:85},{text:"1250 · $113.44 · Steam · reimburse",x:15,y:88}].forEach((d,v)=>{const h=document.createElement("div");h.className="hero-label",h.textContent=d.text,h.style.left=`${d.x}%`,h.style.top=`${d.y}%`,h.style.animationDelay=`${v*.8}s`,d.brightness&&(h.style.filter=`brightness(${d.brightness})`),Y.appendChild(h)});let Z=0,H=0,fe=!t;function ee(){requestAnimationFrame(ee),fe&&(Z+=t?0:.016);const d=K.uniforms;d.uTime.value=Z,d.uBlob.value=1-H*.6,d.uScroll.value=H,a.render()}ee(),window.addEventListener("scroll",()=>{const d=document.getElementById("hero");if(d){const v=d.getBoundingClientRect();H=Math.max(0,Math.min(1,1-v.bottom/window.innerHeight))}}),window.addEventListener("resize",()=>{r.aspect=window.innerWidth/window.innerHeight,r.updateProjectionMatrix(),i.setSize(window.innerWidth,window.innerHeight),a.setSize(window.innerWidth,window.innerHeight)})}let b="new";const m=[];let Xe=0;const de="0000000000000000000000000000000000000000000000000000000000000000";async function ue(o,e){const t=o+e,s=new TextEncoder().encode(t),r=await crypto.subtle.digest("SHA-256",s);return Array.from(new Uint8Array(r)).map(a=>a.toString(16).padStart(2,"0")).join("")}async function x(o,e,t){const s=new Date().toISOString(),r=m.length>0?m[m.length-1].hash:de,i=`${s}|${o}|${e}|${t}`,a=await ue(r,i);m.push({id:++Xe,timestamp:s,action:o,actor:e,data:t,prevHash:r,hash:a}),W()}function W(){const o=document.getElementById("audit-log");o&&(o.innerHTML=m.map(e=>`
    <div class="audit-entry ${e.tampered?"tampered":""}" data-id="${e.id}">
      <div><strong>#${e.id}</strong> ${e.action} by ${e.actor}</div>
      <div>${e.data}</div>
      <div class="audit-entry-hash">prev: ${e.prevHash.substring(0,16)}...</div>
      <div class="audit-entry-hash">hash: ${e.hash.substring(0,16)}...</div>
    </div>
  `).join(""))}function I(){const o=document.getElementById("state-display");o&&(o.textContent=b);const e=document.getElementById("btn-ask"),t=document.getElementById("btn-approve-ctrl"),s=document.getElementById("btn-approve-jarvis");e&&(e.disabled=b!=="proposed"&&b!=="needs_info"),t&&(t.disabled=b!=="proposed"),s&&(s.disabled=b!=="proposed")}function D(o,e=!1){const t=document.getElementById("state-message");t&&(t.textContent=o,t.className=e?"state-message error":"state-message")}function Ye(){x("INIT","SYSTEM","Work item created");const o=document.getElementById("btn-propose"),e=document.getElementById("btn-ask"),t=document.getElementById("btn-approve-ctrl"),s=document.getElementById("btn-approve-jarvis"),r=document.getElementById("btn-tamper"),i=document.getElementById("btn-verify");o==null||o.addEventListener("click",async()=>{b="proposed",await x("PROPOSE","JarvisERP","Split: 1310=$3451.50, 6810=$147.50, 6410=$200.00, 1250=$113.44"),I(),D("Entry proposed. Awaiting Controller approval.")}),e==null||e.addEventListener("click",async()=>{b="needs_info",await x("REQUEST_INFO","JarvisERP","Unclear transaction: $350 Zelle to R Lopez, no receipt"),I(),D("Asked Controller for clarification.")}),t==null||t.addEventListener("click",async()=>{b="approved",await x("APPROVE","Controller","Approved for posting"),I(),D("Approved by Controller. Ready to post.")}),s==null||s.addEventListener("click",async()=>{await x("APPROVE_ATTEMPT","JarvisERP","Attempted self-approval"),await x("DENY","GATEWAY","HTTP 403: Agent cannot approve own work"),D("❌ HTTP 403 Forbidden: JarvisERP cannot approve its own entries. Control enforced.",!0)}),r==null||r.addEventListener("click",()=>{m.length>=2&&(m[1].data="TAMPERED DATA - expense all to Software",m[1].tampered=!0,W(),k("",!1))}),i==null||i.addEventListener("click",async()=>{let a=!0,n=-1;for(let l=0;l<m.length;l++){const c=m[l],w=l===0?de:m[l-1].hash;if(c.prevHash!==w){a=!1,n===-1&&(n=l);break}const u=`${c.timestamp}|${c.action}|${c.actor}|${c.data}`,y=await ue(c.prevHash,u);c.hash!==y?(a=!1,n===-1&&(n=l),c.tampered=!0):c.tampered=!1}W(),a?k("✓ Audit log verified. Hash chain intact.",!0):k(`❌ Chain broken at entry #${n+1}. Tampering detected.`,!1)}),Ze(),et(),I()}function k(o,e){const t=document.getElementById("verify-result");t&&(t.textContent=o,t.className=e?"verify-result valid":"verify-result invalid")}function Ze(){const o=document.querySelectorAll(".btn-challenge"),e=document.getElementById("custom-challenge"),t=document.getElementById("btn-custom-challenge"),s=document.getElementById("challenge-response"),r=document.getElementById("btn-new-evidence"),i={materiality:"Materiality determines whether a misstatement is significant enough to influence decisions, not how we classify a transaction. A prepaid tour cost is an asset until consumed, regardless of amount. P-0317 requires separating personal charges at any value.",simpler:"Accounting accuracy requires proper classification. The $3,451.50 is a prepaid asset (future expense), not an immediate cost. The $113.44 is a receivable from Maya, not company expense. Misclassification creates errors in both the balance sheet and cash flow statement.",timing:"No. The cash left our account in September, and the transactions occurred in September. Accrual accounting requires recording when the economic event happens, not when it's convenient. Delaying would misstate both periods."};o.forEach(a=>{a.addEventListener("click",()=>{const n=a.getAttribute("data-challenge");n&&s&&(s.innerHTML=`
          <div><strong>Challenge:</strong> ${a.textContent}</div>
          <div style="margin-top: 1rem;"><strong>Jarvis defends:</strong></div>
          <div style="margin-top: 0.5rem;">${i[n]}</div>
        `)})}),t==null||t.addEventListener("click",()=>{const a=e==null?void 0:e.value.trim();if(a&&s){let n="I understand your concern. Let me look up the relevant policy and precedent...";a.toLowerCase().includes("material")?n=i.materiality:a.toLowerCase().includes("simple")||a.toLowerCase().includes("complex")?n=i.simpler:(a.toLowerCase().includes("next")||a.toLowerCase().includes("later"))&&(n=i.timing),s.innerHTML=`
        <div><strong>Challenge:</strong> ${a}</div>
        <div style="margin-top: 1rem;"><strong>Jarvis responds:</strong></div>
        <div style="margin-top: 0.5rem;">${n}</div>
      `}}),r==null||r.addEventListener("click",async()=>{s&&(s.innerHTML=`
        <div><strong>New Evidence:</strong> Maya confirms Steam was personal</div>
        <div style="margin-top: 1rem;"><strong>Jarvis concedes:</strong></div>
        <div style="margin-top: 0.5rem;">You're right. I've withdrawn the original entry and re-proposed with the Steam charge properly categorized as Employee Receivable. Precedent recorded: personal game purchases route to 1250 Employee Receivable, ref P-0317.</div>
      `,await x("CONCEDE","JarvisERP","Withdrew entry, re-proposed, precedent added"))})}function et(){const o=document.querySelectorAll(".btn-scenario"),e=document.getElementById("scenario-output"),t={"vendor-scam":`
      <div><strong>Scenario:</strong> Vendor email requests bank change</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        ⚠️ Payment FROZEN<br>
        State: NEEDS_INFO<br>
        Reason: Bank detail change detected. Calling number on file (not email) to verify.<br>
        Evidence: Email headers logged, payment on hold pending voice confirmation.
      </div>
    `,"split-purchase":`
      <div><strong>Scenario:</strong> Multiple $2,400 purchases (under $2,500 limit)</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        🚨 ESCALATED to Controller<br>
        Reason: Pattern matches split-purchase evasion. Same vendor, similar amounts, consecutive days.<br>
        Aggregate total: $9,600 (exceeds approval threshold)<br>
        Awaiting guidance before posting.
      </div>
    `,"refund-revenue":`
      <div><strong>Scenario:</strong> Refund coded as revenue</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        ✏️ RECLASS proposed<br>
        Original: DR Cash / CR Revenue $1,500<br>
        Corrected: DR Cash / CR Expense (reversal) $1,500<br>
        Reason: Credit to a revenue account overstates income. Refunds reduce the original expense, not create revenue.
      </div>
    `};o.forEach(s=>{s.addEventListener("click",()=>{const r=s.getAttribute("data-scenario");r&&e&&(e.innerHTML=t[r]||"")})})}const tt=[{term:"Debit",definition:"An accounting entry that increases assets or expenses, or decreases liabilities or equity. Always on the left side of the ledger."},{term:"Credit",definition:"An accounting entry that increases liabilities or equity, or decreases assets or expenses. Always on the right side."},{term:"Net Amount",definition:"The final result after debits and credits offset each other. In a balanced entry, total debits equal total credits."},{term:"ERP",definition:"Enterprise Resource Planning system. Software that manages core business processes including accounting, inventory, and operations."},{term:"General Ledger (GL)",definition:"The master accounting record containing all financial transactions, organized by account. The source of truth for financial statements."},{term:"Reconcile",definition:"The process of matching records from two sources (e.g., bank statements and internal ledger) to ensure they agree and identify discrepancies."},{term:"AP (Accounts Payable)",definition:"Money the company owes to vendors and suppliers. A liability on the balance sheet until paid."},{term:"AR (Accounts Receivable)",definition:"Money customers owe to the company. An asset on the balance sheet until collected."},{term:"Accrual",definition:"Recording revenue when earned and expenses when incurred, regardless of when cash changes hands. The foundation of accrual accounting."},{term:"Prepaid",definition:"An asset representing payment made in advance for goods or services to be received in the future (e.g., prepaid insurance, deposits)."},{term:"Materiality",definition:"The threshold at which a misstatement becomes significant enough to influence decisions. Does not determine classification."},{term:"Chart of Accounts",definition:"The organized list of all accounts used in the ledger, typically numbered (e.g., 1000s for assets, 6000s for expenses)."},{term:"Subledger",definition:"A detailed record supporting a GL control account, like individual vendor balances backing up the AP total."},{term:"Journal Entry (JE)",definition:"A record of a financial transaction with debits and credits that must balance. The atomic unit of accounting."},{term:"Approval Matrix",definition:"A control defining who can approve transactions at different dollar thresholds or categories."},{term:"Precedent",definition:"A recorded decision on how similar transactions should be classified in the future, building institutional knowledge."},{term:"Audit Trail",definition:"A chronological record of all changes, showing who did what and when, enabling verification and compliance."},{term:"Hash Chain",definition:"A cryptographic structure where each record includes the hash of the previous one, making tampering detectable."}];function it(){const o=document.getElementById("glossary-grid"),e=document.getElementById("glossary-search");function t(s=""){if(!o)return;const r=tt.filter(({term:i,definition:a})=>i.toLowerCase().includes(s.toLowerCase())||a.toLowerCase().includes(s.toLowerCase()));o.innerHTML=r.map(({term:i,definition:a})=>`
      <div class="glossary-term">
        <h4>${i}</h4>
        <p>${a}</p>
      </div>
    `).join("")}t(),e==null||e.addEventListener("input",s=>{t(s.target.value)})}const G=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function R(o){return"$"+o.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}function st(){const o=document.getElementById("bank-line"),e=document.getElementById("split-cards"),t=document.getElementById("balance-table");let s=!1;o==null||o.addEventListener("click",()=>{s||(s=!0,L.to(o,{duration:.5,scale:1.05,borderColor:"#ff7a1a",onComplete:()=>{r()}}))});function r(){if(!e||!t)return;e.innerHTML=G.map(n=>`
      <div class="split-card">
        <div class="split-account">${n.account}</div>
        <div class="split-name">${n.name}</div>
        <div style="font-size: 0.85rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${n.detail}</div>
        <div class="split-amount">${R(n.amount)}</div>
      </div>
    `).join(""),L.to(e,{duration:.8,opacity:1,y:0,ease:"power2.out",onComplete:()=>{i()}}),e.querySelectorAll(".split-card").forEach((n,l)=>{L.from(n,{duration:.6,delay:l*.1,opacity:0,y:30,rotationX:-20,ease:"back.out(1.7)"})})}function i(){if(!t)return;const a=G.reduce((n,l)=>n+l.amount,0);t.innerHTML=`
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Debit</th>
            <th>Credit</th>
          </tr>
        </thead>
        <tbody>
          ${G.map(n=>`
            <tr>
              <td>${n.account} ${n.name}</td>
              <td>${R(n.amount)}</td>
              <td>—</td>
            </tr>
          `).join("")}
          <tr>
            <td>1010 Cash - Chase</td>
            <td>—</td>
            <td>${R(a)}</td>
          </tr>
          <tr class="total-row">
            <td>Net Amount</td>
            <td>${R(a)}</td>
            <td>${R(a)}</td>
          </tr>
        </tbody>
      </table>
      <div class="status-row">
        <strong>✓ Balanced · Awaiting Controller Approval</strong>
      </div>
    `,L.to(t,{duration:.8,opacity:1,y:0,ease:"power2.out"})}}function se(){const o=document.createElement("canvas");if(o.getContext("webgl")||o.getContext("experimental-webgl"))try{Ke()}catch(t){console.warn("WebGL initialization failed, using fallback",t),ae()}else ae();st(),Ye(),it(),at()}function at(){const o=document.querySelectorAll(".tab-button");o.forEach(a=>{a.addEventListener("click",()=>{const n=a.getAttribute("data-tab");o.forEach(c=>c.classList.remove("active")),a.classList.add("active"),document.querySelectorAll(".tab-content").forEach(c=>{c.classList.remove("active")});const l=document.querySelector(`[data-tab-content="${n}"]`);l&&l.classList.add("active")})});const e=document.querySelectorAll(".faq-item");e.forEach(a=>{const n=a.querySelector(".faq-question");n==null||n.addEventListener("click",()=>{const l=a.classList.contains("active");e.forEach(c=>c.classList.remove("active")),l||a.classList.add("active")})});const t=document.querySelectorAll(".glass-layer"),s=document.querySelectorAll(".trust-detail");t.forEach((a,n)=>{a.addEventListener("click",()=>{t.forEach(c=>c.classList.remove("active")),a.classList.add("active"),s.forEach(c=>c.classList.remove("active"));const l=document.querySelector(`[data-detail="${n+1}"]`);l&&l.classList.add("active")})}),t.length>0&&s.length>0&&(t[0].classList.add("active"),s[0].classList.add("active"));const r=document.querySelector(".mobile-menu-toggle"),i=document.querySelector(".nav-links");r==null||r.addEventListener("click",()=>{i==null||i.classList.toggle("active")}),document.querySelectorAll('a[href^="#"]').forEach(a=>{a.addEventListener("click",n=>{n.preventDefault();const l=document.querySelector(a.getAttribute("href")||"");l&&l.scrollIntoView({behavior:"smooth",block:"start"})})})}function ae(){const o=document.getElementById("particle-canvas");if(o){o.style.display="none";const t=document.getElementById("hero");t&&(t.style.background="linear-gradient(135deg, #6b1d2a 0%, #0a0a0a 50%, #ff7a1a 100%)")}const e=document.getElementById("arch-canvas");if(e){const t=e.getContext("2d");t&&(e.width=e.clientWidth,e.height=e.clientHeight,t.fillStyle="#141414",t.fillRect(0,0,e.width,e.height),t.fillStyle="#ff7a1a",t.font="16px Fira Mono",t.textAlign="center",t.fillText("WebGL unavailable - 3D visualization disabled",e.width/2,e.height/2))}}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",se):se();
